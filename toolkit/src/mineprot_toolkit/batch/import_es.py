"""Import directory metadata into Elasticsearch through MineProt's API."""

import argparse
import base64
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mineprot_toolkit.common import api
from mineprot_toolkit.common.annotations import uniprot_to_mineprot
from mineprot_toolkit.common.defaults import ES_URL
from mineprot_toolkit.common.sequences import pdb2seq


def build_parser():
    parser = argparse.ArgumentParser(description="Import your proteins into Elasticsearch.")
    parser.add_argument("-i", required=True, type=Path, help="Preprocessed input directory")
    parser.add_argument("-n", help="Index name; defaults to the input directory name")
    parser.add_argument("-a", action="store_true", help="Annotate using the UniProt API")
    parser.add_argument("-f", action="store_true", help="Delete the existing index before import")
    parser.add_argument("-t", type=int, default=1, help="Worker threads")
    parser.add_argument("--max-msa", type=int, default=10)
    parser.add_argument("--url", default=ES_URL)
    return parser


def import_protein(path, args):
    name = path.stem
    document_id = base64.b64encode(name.encode()).decode()
    response = api.es_get(args.url, args.n, document_id).json()
    if response.get("found"):
        print(f"Skipping {name}...")
        return
    document = {
        "name": name,
        "seq": pdb2seq(path),
        "score": -1.0,
        "anno": {"homolog": "", "database": "", "description": []},
    }
    with path.with_suffix(".json").open() as stream:
        scores = json.load(stream)["plddt"]
        document["score"] = sum(scores) / len(scores)
    if args.a:
        with path.with_suffix(".a3m").open() as stream:
            identifiers = [line for line in stream if line.startswith(">")]
        document["anno"] = uniprot_to_mineprot(identifiers[1:], args.max_msa)
    if name not in document["anno"]["description"]:
        document["anno"]["description"].append(name)
    api.es_add(args.url, args.n, document_id, json.dumps(document))
    print(f"Imported {name}")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.i.is_dir() or args.t < 1 or args.max_msa < 1:
        parser.error("-i must be a directory; -t and --max-msa must be positive")
    args.n = args.n or args.i.resolve().name
    if args.f:
        print(f"WARNING: ALL INDEX DATA IN {args.n} WILL BE OVERWRITTEN.")
        api.es_delete(args.url, args.n)
    failures = 0
    with ThreadPoolExecutor(max_workers=args.t) as pool:
        futures = {
            pool.submit(import_protein, path, args): path
            for path in sorted(args.i.glob("*.pdb"))
            if path.is_file()
        }
        for future, path in futures.items():
            try:
                future.result()
            except Exception as exc:
                failures += 1
                print(f"Error importing {path.name}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
