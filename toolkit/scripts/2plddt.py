import os
import sys
import argparse
import json
from pathlib import Path
import gzip
import lzma
import bz2
from concurrent.futures import ProcessPoolExecutor

try:
    from Bio.PDB import MMCIFParser
    from Bio.PDB.PDBParser import PDBParser
except ImportError:
    MMCIFParser = None
    PDBParser = None


def open_file(path):
    if path.suffix == '.gz':
        return gzip.open(path, 'rt')
    if path.suffix == '.xz':
        return lzma.open(path, 'rt')
    if path.suffix == '.bz2':
        return bz2.open(path, 'rt')
    return open(path, 'rt')


def extract_json_plddt(path, residue=False):
    with open_file(path) as f:
        data = json.load(f)
    plddt = data.get('plddt')
    if plddt is None:
        raise KeyError(f"No 'plddt' key in JSON: {path}")
    if residue:
        return plddt
    return sum(plddt) / len(plddt) if plddt else 0


def extract_structure_plddt(path, residue=False):
    ext = path.suffix.lower()
    if ext in ['.cif', '.bcif'] and MMCIFParser:
        parser = MMCIFParser()
        struct = parser.get_structure(path.stem, str(path))
    elif ext in ['.pdb'] and PDBParser:
        parser = PDBParser(QUIET=True)
        struct = parser.get_structure(path.stem, str(path))
    else:
        return extract_pdb_plddt_manual(path, residue)

    res_plddt = []
    for model in struct:
        for chain in model:
            for res in chain:
                atoms = list(res.get_atoms())
                if not atoms:
                    continue
                vals = [atom.get_bfactor() for atom in atoms]
                avg = sum(vals) / len(vals)
                res_plddt.append(avg)
    if residue:
        return res_plddt
    return sum(res_plddt) / len(res_plddt) if res_plddt else 0


def extract_pdb_plddt_manual(path, residue=False):
    res_dict = {}
    with open_file(path) as f:
        for line in f:
            if not (line.startswith('ATOM') or line.startswith('HETATM')):
                continue
            chain = line[21]
            resseq = line[22:26].strip()
            key = (chain, resseq)
            try:
                b = float(line[60:66])
            except ValueError:
                continue
            res_dict.setdefault(key, []).append(b)
    vals = []
    for key in sorted(res_dict):
        atoms = res_dict[key]
        if atoms:
            vals.append(sum(atoms) / len(atoms))
    if residue:
        return vals
    return sum(vals) / len(vals) if vals else 0


def process_item(name, info, residue=False):
    path, kind = info
    try:
        if kind == 'json':
            result = extract_json_plddt(path, residue)
        else:
            result = extract_structure_plddt(path, residue)
        return name, result
    except Exception as e:
        return name, f"ERROR: {e}"


def main():
    parser = argparse.ArgumentParser(description="Extract pLDDT scores from JSON or structure files.")
    parser.add_argument('-i', '--input', required=True, help='Input directory')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')
    parser.add_argument('-t', '--threads', type=int, default=1, help='Number of processes')
    parser.add_argument('--residue', action='store_true', help='Output per-residue pLDDT values')
    parser.add_argument('--nameless', action='store_true', help='Only output scores, omit file names')
    args = parser.parse_args()

    indir = Path(args.input)
    if not indir.is_dir():
        print(f"Error: input directory not found: {indir}", file=sys.stderr)
        sys.exit(1)

    # map file prefix to preferred file (json > pdb > cif)
    priority = ['.json', '.pdb', '.cif']
    extensions = ['.json', '.json.gz', '.json.xz', '.json.bz2',
                  '.pdb', '.pdb.gz', '.pdb.xz', '.pdb.bz2',
                  '.cif', '.cif.gz', '.cif.xz', '.cif.bz2']

    seen = {}
    for f in indir.rglob('*'):
        if not f.is_file():
            continue
        for ext in extensions:
            if f.name.endswith(ext):
                prefix = f.name[: -len(ext)]
                ext_type = '.' + ext.split('.')[1] if '.' in ext else ext
                if prefix not in seen:
                    seen[prefix] = (f, 'json' if ext_type == '.json' else 'struct', priority.index(ext_type))
                else:
                    existing = seen[prefix]
                    if priority.index(ext_type) < existing[2]:
                        seen[prefix] = (f, 'json' if ext_type == '.json' else 'struct', priority.index(ext_type))
                break

    items = {prefix: (info[0], info[1]) for prefix, info in seen.items()}

    results = []
    with ProcessPoolExecutor(max_workers=args.threads) as executor:
        futures = [executor.submit(process_item, name, info, args.residue)
                   for name, info in items.items()]
        for future in futures:
            results.append(future.result())

    out_lines = []
    for name, res in sorted(results):
        if isinstance(res, list):
            vals = '\t'.join(str(v) for v in res)
            line = vals if args.nameless else f"{name}\t{vals}"
        else:
            line = str(res) if args.nameless else f"{name}\t{res}"
        out_lines.append(line)

    if args.output:
        with open(args.output, 'w') as wf:
            wf.write("\n".join(out_lines))
    else:
        for line in out_lines:
            print(line)

if __name__ == '__main__':
    main()
