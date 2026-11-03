"""Repository access shared by HTTP handlers and background jobs."""
import base64
import gzip
import io
import os
import subprocess
import tempfile
from pathlib import Path

from . import settings


def component(value: str) -> str:
    if not value or value in (".", "..") or any(c in value for c in ("/", "\\", "\x00")):
        raise ValueError("Invalid repository or file name")
    return value


def inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Path outside permitted directory")
    return path


def repo_file(repo: str, name: str) -> Path:
    return inside(settings.REPO_ROOT, component(repo) + "/" + component(name))


def b64decode(value: str) -> bytes:
    # PHP query parsing turns literal '+' into spaces; accept legacy unescaped links.
    return base64.b64decode(value.replace(" ", "+"), validate=True)


def bounded_gunzip(data: bytes) -> bytes:
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
        result = stream.read(settings.MAX_BODY + 1)
    if len(result) > settings.MAX_BODY:
        raise ValueError("Decompressed data exceeds size limit")
    return result


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".mineprot-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def decompress_fcz(data: bytes) -> bytes:
    with tempfile.TemporaryDirectory(prefix="MP_FCZ_") as temporary:
        source = Path(temporary) / "input.fcz"
        output = Path(temporary) / "output.pdb"
        source.write_bytes(data)
        subprocess.run([settings.FOLDCOMP, "decompress", str(source), str(output)],
                       check=True, capture_output=True, timeout=settings.JOB_TIMEOUT)
        return output.read_bytes()


def read_file(repo: str, name: str) -> bytes:
    path = repo_file(repo, name)
    suffix = path.suffix.lower()
    if suffix not in (".pdb", ".cif", ".json", ".a3m", ".fcz", ".gz"):
        raise ValueError("Unsupported file type")
    if path.is_file():
        data = path.read_bytes()
        if suffix == ".gz":
            return gzip.decompress(data)
        if suffix == ".fcz":
            return decompress_fcz(data)
        return data
    compressed = repo_file(repo, name + ".gz")
    if compressed.is_file():
        return gzip.decompress(compressed.read_bytes())
    if suffix == ".pdb":
        fcz = repo_file(repo, path.stem + ".fcz")
        if fcz.is_file():
            return decompress_fcz(fcz.read_bytes())
        fcz_gz = repo_file(repo, path.stem + ".fcz.gz")
        if fcz_gz.is_file():
            return decompress_fcz(gzip.decompress(fcz_gz.read_bytes()))
        # CIF-only repositories can also participate in structure searches.
        cif = repo_file(repo, path.stem + ".cif")
        if cif.is_file() or repo_file(repo, path.stem + ".cif.gz").is_file():
            from .structures import cif_to_pdb
            return cif_to_pdb(read_file(repo, path.stem + ".cif")).encode()
    if suffix == ".cif":
        from .structures import pdb_to_alphacif
        return pdb_to_alphacif(read_file(repo, path.stem + ".pdb"), path.stem).encode()
    raise FileNotFoundError(name)


def protein_names(repo: str) -> list[str]:
    directory = inside(settings.REPO_ROOT, component(repo))
    if not directory.is_dir():
        raise FileNotFoundError(repo)
    names = set()
    for path in directory.iterdir():
        if not path.is_file():
            continue
        name = path.name.removesuffix(".gz")
        if Path(name).suffix.lower() in (".pdb", ".fcz", ".cif"):
            names.add(Path(name).stem)
    return sorted(names)
