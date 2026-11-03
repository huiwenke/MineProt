"""US-align jobs with filesystem state, bounded workers and atomic archives."""
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import traceback
import uuid
from pathlib import Path

from . import settings
from .storage import atomic_write, component, inside, read_file
from .structures import cif_to_pdb


def job_path(rid: str) -> Path:
    if not rid or any(c not in "0123456789abcdef" for c in rid):
        raise ValueError("Invalid job ID")
    return inside(settings.CACHE_ROOT, "MP_SALIGN_" + rid)


def state(directory: Path, value: str) -> None:
    atomic_write(directory / "status.txt", value.encode())


def job_hinge(directory: Path) -> int:
    options = directory / "options.json"
    # Jobs created before this option was exposed always used 9.
    return json.loads(options.read_text())["hinge"] if options.is_file() else 9


def submit(structure: str, targets: list[dict], hinge: int = 0) -> str:
    if type(hinge) is not int or not 0 <= hinge <= 9:
        raise ValueError("Hinge must be an integer between 0 and 9")
    structure = structure.lstrip("\ufeff \t\r\n")
    if any(line.strip().lower().startswith(("data_", "_atom_site."))
           for line in structure.splitlines()):
        try:
            structure = cif_to_pdb(structure.encode())
        except (RuntimeError, ValueError) as exc:
            raise ValueError(f"Invalid CIF query structure: {exc}") from exc
    rid = uuid.uuid4().hex
    directory = job_path(rid)
    directory.mkdir(parents=True)
    atomic_write(directory / "query.pdb", structure.encode())
    atomic_write(directory / "targets.json", json.dumps(targets).encode())
    atomic_write(directory / "options.json", json.dumps({"hinge": hinge}).encode())
    atomic_write(directory / "total.txt", str(len(targets)).encode())
    atomic_write(directory / "progress.txt", b"0")
    state(directory, "queued")
    with (directory / "query.err").open("ab") as errors:
        try:
            process = subprocess.Popen([sys.executable, "-m", "mineprot.jobs", rid],
                             cwd=settings.WEB_ROOT, stdin=subprocess.DEVNULL,
                             stdout=errors, stderr=errors, start_new_session=True)
            atomic_write(directory / "pid.txt", str(process.pid).encode())
        except Exception:
            state(directory, "failed")
            raise
    return rid


def worker(rid: str) -> None:
    directory = job_path(rid)
    lock = None
    try:
        # flock is shared between Uvicorn workers and survives neither crashes
        # nor process exit. Waiting jobs do not consume a US-align slot.
        while lock is None:
            for slot in range(max(1, settings.MAX_JOBS)):
                candidate = (settings.CACHE_ROOT / f"salign-slot-{slot}.lock").open("a")
                try:
                    fcntl.flock(candidate, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    lock = candidate
                    break
                except BlockingIOError:
                    candidate.close()
            if lock is None:
                time.sleep(1)
        state(directory, "running")
        targets = json.loads((directory / "targets.json").read_text())
        hinge = job_hinge(directory)
        failed = 0
        with (directory / "query.out").open("w") as output:
            for index, target in enumerate(targets, 1):
                repo, name = component(target["repo"]), component(target["name"])
                target_path = inside(directory, repo + "/" + name + ".pdb")
                target_path.parent.mkdir(parents=True, exist_ok=True)
                # Prefix includes repository, avoiding collisions between equal names.
                prefix = target_path.parent / ("query_" + name)
                try:
                    atomic_write(target_path, read_file(repo, name + ".pdb"))
                    result = subprocess.run([
                        settings.USALIGN, str(directory / "query.pdb"), str(target_path),
                        "-mm", "7", "-afp", "-hinge", str(hinge), "-fast", "-outfmt", "2",
                        "-o", str(prefix)], capture_output=True, text=True,
                        timeout=settings.JOB_TIMEOUT, check=True)
                    output.write(result.stdout)
                    output.flush()
                    if result.stderr:
                        print(result.stderr, file=sys.stderr)
                except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                    failed += 1
                    print(f"Failed target {repo}/{name}: {exc}", file=sys.stderr)
                finally:
                    target_path.unlink(missing_ok=True)
                    atomic_write(directory / "progress.txt", str(index).encode())
        if targets and failed == len(targets):
            raise RuntimeError("All alignment targets failed")
        # Keep paths in PyMOL files relative to the archive directory.
        for path in directory.rglob("*.pml"):
            text = path.read_text().replace(str(directory) + "/", "")
            path.write_text(text)
        state(directory, "packaging")
        fd, archive_name = tempfile.mkstemp(prefix="MP_SALIGN_ARCHIVE_", dir=settings.CACHE_ROOT)
        os.close(fd)
        try:
            with tarfile.open(archive_name, "w:gz") as archive:
                for path in sorted(directory.rglob("*")):
                    if path.is_file() and path.name not in ("result.tar.gz", "query.err", "status.txt"):
                        archive.add(path, arcname=str(path.relative_to(directory)), recursive=False)
            os.replace(archive_name, directory / "result.tar.gz")
        finally:
            Path(archive_name).unlink(missing_ok=True)
        state(directory, "complete")
    except Exception:
        traceback.print_exc()
        state(directory, "failed")
    finally:
        if lock is not None:
            lock.close()


def status(directory: Path) -> str:
    value = (directory / "status.txt").read_text().strip()
    if value in ("queued", "running", "packaging"):
        pid_file = directory / "pid.txt"
        if pid_file.is_file():
            # Check the command as well as the PID to avoid PID reuse after restart.
            try:
                command = Path("/proc") / pid_file.read_text().strip() / "cmdline"
                arguments = command.read_bytes().split(b"\x00")
                rid = directory.name.removeprefix("MP_SALIGN_").encode()
                if b"mineprot.jobs" not in arguments or rid not in arguments:
                    raise ProcessLookupError("Worker no longer exists")
            except (OSError, ValueError):
                # A worker may have completed between reading state and its PID.
                latest = (directory / "status.txt").read_text().strip()
                if latest in ("queued", "running", "packaging"):
                    state(directory, "failed")
                    return "failed"
                return latest
    return value


def cleanup() -> None:
    for directory in settings.CACHE_ROOT.glob("MP_SALIGN_*"):
        status_file = directory / "status.txt"
        if directory.is_dir() and status_file.is_file() and status(directory) in ("complete", "failed"):
            if time.time() - status_file.stat().st_mtime > 86400:
                shutil.rmtree(directory)


def results(rid: str, threshold: float) -> list[dict]:
    directory = job_path(rid)
    hits = []
    for line in (directory / "query.out").read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) < 11:
            continue
        try:
            scores = [float(value) for value in fields[2:11]]
        except ValueError:
            continue
        if max(scores[:2]) < threshold:
            continue
        # US-align adds a chain selector after the coordinate filename.
        target = fields[1].strip().rsplit(".pdb", 1)[0] + ".pdb"
        relative = inside(directory, target).relative_to(directory)
        repo, name = relative.parent.name, Path(relative.name).stem
        prefix = f"MP_SALIGN_{rid}/{repo}/query_{name}"
        hit = dict(zip(("TM1", "TM2", "RMSD", "ID1", "ID2", "IDali", "L1", "L2", "Lali"), scores))
        hit.update(repo=repo, name=name, prefix=prefix,
                   query=str(settings.CACHE_ROOT / (prefix + ".pdb")), target=str(directory / relative))
        hits.append(hit)
    return sorted(hits, key=lambda hit: (hit["TM1"] + hit["TM2"]) / 2, reverse=True)


if __name__ == "__main__":
    worker(sys.argv[1])
