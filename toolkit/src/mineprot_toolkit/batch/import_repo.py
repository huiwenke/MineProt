"""Import repository files using bounded, retryable binary batches."""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mineprot_toolkit.common.defaults import IMPORT_URL
from mineprot_toolkit.common.uploads import prepare, upload_batch


def parser():
    result = argparse.ArgumentParser(description="Import proteins using batch transfers.")
    result.add_argument("-i", required=True, type=Path, help="Directory of preprocessed files")
    result.add_argument("-n", help="Repository name; defaults to the input directory name")
    result.add_argument(
        "-m",
        type=int,
        choices=range(5),
        default=0,
        help="0: all; 1: no A3M; 2: PDB/JSON; 3: PDB; 4: PDB compressed to FCZ",
    )
    result.add_argument(
        "-f", action="store_true", help="Overwrite different content in the same storage format"
    )
    result.add_argument(
        "-z", action="store_true", help="Store files as gzip on the server (incompatible with -m 4)"
    )
    result.add_argument("--url", default=IMPORT_URL)
    result.add_argument("--batch-files", type=int, default=256, help="Files per batch, 1 to 256")
    result.add_argument(
        "--batch-mib", type=float, default=16, help="Target multipart batch size in MiB"
    )
    result.add_argument("--workers", type=int, default=2, help="Concurrent upload batches, 1 to 8")
    return result


def main(argv=None):
    options = parser()
    args = options.parse_args(argv)
    if args.m == 4 and args.z:
        options.error("-z and -m 4 cannot be used together; .fcz.gz is not supported")
    if not args.i.is_dir():
        options.error("-i must be an existing directory")
    if not 1 <= args.batch_files <= 256 or not 1 <= args.workers <= 8:
        options.error("--batch-files must be 1..256 and --workers must be 1..8")
    if not 0 < args.batch_mib <= 64:
        options.error("--batch-mib must be greater than 0 and at most 64")
    args.n = args.n or args.i.resolve().name
    if args.m == 4:
        try:
            import importlib.metadata

            if importlib.metadata.version("foldcomp") != "1.0.0":
                options.error("Mode 4 requires foldcomp==1.0.0 for consistent FCZ checksums")
        except importlib.metadata.PackageNotFoundError:
            options.error("Mode 4 requires: pip install foldcomp==1.0.0")
    suffixes = {
        0: {".a3m", ".cif", ".json", ".pdb"},
        1: {".cif", ".json", ".pdb"},
        2: {".json", ".pdb"},
        3: {".pdb"},
        4: {".pdb"},
    }[args.m]
    counts = {"imported": 0, "unchanged": 0, "exists": 0, "error": 0}

    def report(results):
        for result in results:
            status = result["status"]
            if status not in counts:
                raise RuntimeError("Unexpected upload status: " + str(status))
            counts[status] += 1
            print(
                status
                + " "
                + args.n
                + "/"
                + result["name"]
                + (": " + result["error"] if status == "error" else "")
            )

    def complete(future, names):
        try:
            report(future.result())
        except Exception as exc:
            report([{"name": name, "status": "error", "error": str(exc)} for name in names])

    # Bound queued payloads instead of submitting the entire directory at once.
    outstanding = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        batch, size = [], 4096

        def submit():
            if len(outstanding) >= args.workers:
                complete(*outstanding.pop(0))
            outstanding.append(
                (pool.submit(upload_batch, args, list(batch)), [item["name"] for item, _ in batch])
            )

        for path in sorted(args.i.iterdir()):
            if not path.is_file() or path.suffix not in suffixes:
                continue
            try:
                item, payload = prepare(path, args.m, args.z)
            except Exception as exc:
                report(
                    [
                        {
                            "name": path.name,
                            "status": "error",
                            "error": "Compression/read failed: " + str(exc),
                        }
                    ]
                )
                continue
            cost = len(payload) + len(json.dumps(item).encode()) + 1024
            if batch and (
                len(batch) >= args.batch_files or size + cost > args.batch_mib * 1024 * 1024
            ):
                submit()
                batch, size = [], 4096
            batch.append((item, payload))
            size += cost
        if batch:
            submit()
        for future, names in outstanding:
            complete(future, names)
    print("Done: " + ", ".join(str(count) + " " + status for status, count in counts.items()))
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
