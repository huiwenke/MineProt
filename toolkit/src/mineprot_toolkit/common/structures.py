"""Structure parsing and confidence scoring shared by import commands."""

import gzip
import math
import re
import subprocess
import sys
from pathlib import Path


def load_structure(path):
    """Read PDB/CIF (optionally gzip) or decode FCZ in an isolated process."""
    path = Path(path)
    data = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix == ".gz":
        data = gzip.decompress(data)
        suffix = path.with_suffix("").suffix.lower()
    if suffix == ".fcz":
        if path.suffix.lower() == ".gz":
            raise ValueError("FCZ + gzip storage is not supported")
        if not data.startswith(b"FCMP"):
            raise ValueError(f"Invalid FCZ file: {path.name}")
        # A malformed FCZ can crash the native decoder; keep worker threads alive.
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys, foldcomp; "
                "sys.stdout.buffer.write(foldcomp.decompress(sys.stdin.buffer.read())[1].encode())",
            ],
            input=data,
            capture_output=True,
            timeout=300,
        )
        if result.returncode:
            raise ValueError(
                f"Cannot decode {path.name}: FCZ decoder exited with {result.returncode}"
            )
        data, suffix = result.stdout, ".pdb"
    if suffix not in (".pdb", ".cif", ".mmcif"):
        raise ValueError(f"Unsupported structure format: {path.name}")
    return parse_structure(data, suffix)


def parse_structure(data, suffix):
    try:
        import gemmi
    except ImportError as exc:
        raise RuntimeError("Gemmi is required: pip install gemmi==0.7.1") from exc
    text = data.decode("utf-8-sig")
    block = None
    if suffix == ".pdb":
        structure = gemmi.read_pdb_string(text)
    else:
        block = gemmi.cif.read_string(text).sole_block()
        structure = gemmi.make_structure_from_block(block)
    if not len(structure) or not any(len(residue) for chain in structure[0] for residue in chain):
        raise ValueError("No atomic coordinates were found in the structure")
    return structure, block


def protein_residues(structure):
    import gemmi

    return [
        residue
        for chain in structure[0]
        for residue in chain
        if len(residue) and gemmi.find_tabulated_residue(residue.name).is_amino_acid()
    ]


def calculate_score(structure, block):
    """Use explicit ModelCIF pLDDT, else one C-alpha B-factor per residue."""
    residues = protein_residues(structure)
    if not residues:
        raise ValueError("No amino-acid residues are available for pLDDT calculation")
    if block is not None:
        metrics = block.get_mmcif_category("_ma_qa_metric.")
        local = block.get_mmcif_category("_ma_qa_metric_local.")
        metric_id = None
        for i, identifier in enumerate(metrics.get("id", [])):
            name = str(metrics.get("name", [""] * len(metrics["id"]))[i]).lower()
            kind = str(metrics.get("type", [""] * len(metrics["id"]))[i]).lower()
            mode = str(metrics.get("mode", ["local"] * len(metrics["id"]))[i]).lower()
            if mode == "local" and ("plddt" in name or kind == "plddt"):
                metric_id = identifier
                break
        if metric_id is not None:
            if not all(
                key in local
                for key in ("metric_id", "label_asym_id", "label_seq_id", "metric_value")
            ):
                raise ValueError("CIF declares per-residue pLDDT but its metric data is incomplete")
            values = {}
            model_id = str(structure[0].num)
            for i, identifier in enumerate(local.get("metric_id", [])):
                if identifier != metric_id:
                    continue
                models = local.get("model_id")
                if models and str(models[i]) != model_id:
                    continue
                key = (str(local["label_asym_id"][i]), int(local["label_seq_id"][i]))
                value = float(local["metric_value"][i])
                if key in values and values[key] != value:
                    raise ValueError("CIF contains conflicting per-residue pLDDT values")
                values[key] = value
            try:
                scores = [values[(residue.subchain, residue.label_seq)] for residue in residues]
            except KeyError as exc:
                raise ValueError(
                    "Explicit CIF pLDDT metrics do not cover all protein residues"
                ) from exc
            source = "CIF ModelCIF pLDDT (mean per residue)"
        else:
            scores = None
    else:
        scores = None
    if scores is None:
        scores = []
        for residue in residues:
            atoms = [atom for atom in residue if atom.element.name not in ("H", "D", "T")]
            ca = next((atom for atom in atoms if atom.name == "CA"), None)
            if not atoms:
                raise ValueError("A protein residue has no readable heavy-atom B-factors")
            scores.append(
                float(ca.b_iso)
                if ca is not None
                else math.fsum(atom.b_iso for atom in atoms) / len(atoms)
            )
        source = "C-alpha B-factor (mean per residue; heavy-atom mean if C-alpha is absent)"
    if not scores or any(not math.isfinite(value) or not 0 <= value <= 100 for value in scores):
        raise ValueError(
            "pLDDT must contain finite values in [0, 100]; check the input or disable calculation"
        )
    return math.fsum(scores) / len(scores), source


PLDDT_KEYS = (
    "plddt",
    "plddts",
    "residueplddt",
    "residueplddts",
    "atomplddts",
    "atomplddt",
    "predictedlddt",
    "meanplddt",
)


def json_score(payload):
    """Find named confidence fields, including nested AF2/AF3 JSON objects."""
    candidates = []
    pending = [(payload, "$")]
    while pending:
        node, path = pending.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                normalized = re.sub(r"[\s_-]", "", key).lower()
                location = f"{path}.{key}"
                if normalized in PLDDT_KEYS:
                    candidates.append((PLDDT_KEYS.index(normalized), location, value))
                elif normalized not in ("pae", "predictedalignederror", "distogram"):
                    if isinstance(value, (dict, list)):
                        pending.append((value, location))
        elif isinstance(node, list):
            pending.extend(
                (node[i], f"{path}[{i}]")
                for i in range(len(node) - 1, -1, -1)
                if isinstance(node[i], (dict, list))
            )
    # Prefer per-residue pLDDT, then per-atom values, then a supplied mean.
    for _, location, field in sorted(candidates, key=lambda item: item[0]):
        if field is None or field == []:
            continue
        values = []
        pending_values = [field]
        while pending_values:
            value = pending_values.pop()
            if isinstance(value, list):
                pending_values.extend(value)
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                value = float(value)
                if not math.isfinite(value) or not 0 <= value <= 100:
                    raise ValueError(f"{location} contains pLDDT outside the finite range [0, 100]")
                values.append(value)
            else:
                raise ValueError(f"{location} must be a number or an array of pLDDT numbers")
        if values:
            return math.fsum(values) / len(
                values
            ), f"JSON {location} (mean of {len(values)} values)"
    return None
