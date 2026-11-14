"""Prepare a directory of models for a 3D-Beacons client."""

import argparse
import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mineprot_toolkit.common.annotations import make_beacon_metadata


def prepare_model(path, output, max_msa):
    created_date = time.strftime("%Y-%m-%d", time.localtime(path.stat().st_ctime))
    with path.with_suffix(".json").open() as stream:
        scores = json.load(stream)["plddt"]
    with path.with_suffix(".a3m").open() as stream:
        lines = stream.readlines()
    metadata = make_beacon_metadata(
        lines[2].strip(), sum(scores) / len(scores), created_date, lines[3::2], max_msa
    )
    if not metadata["mappingAccession"]:
        raise ValueError(f"No mapping accession found for {path.stem}")
    shutil.copyfile(path, output / "pdb" / path.name)
    (output / "metadata" / (path.stem + ".json")).write_text(json.dumps(metadata))
    print(f"{path.stem}: {metadata['mappingAccession']}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepare metadata for a 3D-Beacons client.")
    parser.add_argument("-i", required=True, type=Path, help="MineProt repository directory")
    parser.add_argument("-o", required=True, type=Path, help="3D-Beacons output directory")
    parser.add_argument("-t", type=int, default=1, help="Worker threads")
    parser.add_argument("--max-msa", type=int, default=50)
    args = parser.parse_args(argv)
    if not args.i.is_dir() or args.t < 1 or args.max_msa < 1:
        parser.error("-i must be a directory; -t and --max-msa must be positive")
    for name in ("pdb", "cif", "metadata", "index"):
        (args.o / name).mkdir(parents=True, exist_ok=True)
    failures = 0
    with ThreadPoolExecutor(max_workers=args.t) as pool:
        futures = {
            pool.submit(prepare_model, path, args.o, args.max_msa): path
            for path in sorted(args.i.glob("*.pdb"))
            if path.is_file()
        }
        for future, path in futures.items():
            try:
                future.result()
            except Exception as exc:
                failures += 1
                print(f"Error processing {path.name}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
