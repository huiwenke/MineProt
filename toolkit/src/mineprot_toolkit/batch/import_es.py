"""Import directory metadata into Elasticsearch through MineProt's API."""

import argparse
import base64
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mineprot_toolkit.common import api
from mineprot_toolkit.common.annotations import uniprot_to_mineprot
from mineprot_toolkit.common.defaults import ES_URL
from mineprot_toolkit.common.files import open_text
from mineprot_toolkit.common.sequences import structure_sequence
from mineprot_toolkit.common.structures import calculate_score, json_score, load_structure

STRUCTURE_SUFFIXES = (".cif", ".cif.gz", ".mmcif", ".mmcif.gz", ".pdb", ".pdb.gz", ".fcz")


def structure_name(path):
    for suffix in STRUCTURE_SUFFIXES:
        if path.name.lower().endswith(suffix):
            return path.name[: -len(suffix)]
    raise ValueError(f"Unsupported structure file: {path.name}")


def find_structures(directory):
    """Choose one source per protein, preferring CIF, then PDB, then FCZ."""
    selected = {}
    paths = sorted(directory.iterdir())
    for suffix in STRUCTURE_SUFFIXES:
        for path in paths:
            if path.is_file() and path.name.lower().endswith(suffix):
                selected.setdefault(structure_name(path), path)
    return [selected[name] for name in sorted(selected)]


def companion(directory, name, suffix):
    for ending in (suffix, suffix + ".gz"):
        path = directory / (name + ending)
        if path.is_file():
            return path
    return None


def build_parser():
    parser = argparse.ArgumentParser(description="Import your proteins into Elasticsearch.")
    parser.add_argument(
        "-i", required=True, type=Path, help="Repository of PDB, CIF or FCZ structures"
    )
    parser.add_argument("-n", help="Index name; defaults to the input directory name")
    parser.add_argument("-a", action="store_true", help="Annotate using the UniProt API")
    parser.add_argument("-f", action="store_true", help="Delete the existing index before import")
    parser.add_argument("-t", type=int, default=1, help="Worker threads")
    parser.add_argument("--max-msa", type=int, default=10)
    parser.add_argument("--url", default=ES_URL)
    return parser


def import_protein(path, args):
    name = structure_name(path)
    document_id = base64.b64encode(name.encode()).decode()
    response = api.es_get(args.url, args.n, document_id).json()
    if response.get("found"):
        print(f"Skipping {name}...")
        return
    structure, block = load_structure(path)
    document = {
        "name": name,
        "seq": structure_sequence(structure),
        "score": -1.0,
        "anno": {"homolog": "", "database": "", "description": []},
    }
    confidence = companion(path.parent, name, ".json")
    score = None
    if confidence is not None:
        with open_text(confidence) as stream:
            score = json_score(json.load(stream))
    document["score"] = score[0] if score is not None else calculate_score(structure, block)[0]
    if args.a:
        msa = companion(path.parent, name, ".a3m")
        if msa is not None:
            with open_text(msa) as stream:
                identifiers = [line for line in stream if line.startswith(">")]
            document["anno"] = uniprot_to_mineprot(identifiers[1:], args.max_msa)
        else:
            print(f"No A3M for {name}; importing without UniProt annotation")
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
    structures = find_structures(args.i)
    if not structures:
        parser.error("-i contains no supported PDB, CIF or FCZ structures")
    if args.f:
        print(f"WARNING: ALL INDEX DATA IN {args.n} WILL BE OVERWRITTEN.")
        api.es_delete(args.url, args.n)
    failures = 0
    with ThreadPoolExecutor(max_workers=args.t) as pool:
        futures = {pool.submit(import_protein, path, args): path for path in structures}
        for future, path in futures.items():
            try:
                future.result()
            except Exception as exc:
                failures += 1
                print(f"Error importing {path.name}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
