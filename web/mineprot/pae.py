"""Map PAE tokens to polymer residues or non-polymer atoms for Mol*."""
from collections import defaultdict

import gemmi


def _cell(table, key, index, default=""):
    column = table.get(key, [])
    item = column[index] if index < len(column) else None
    return default if item in (None, False, "", ".", "?") else str(item)


def _number(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _polymer_kinds(block):
    polymers = block.get_mmcif_category("_entity_poly.")
    result = {}
    for i, entity in enumerate(polymers.get("entity_id", [])):
        kind = _cell(polymers, "type", i).lower()
        result[entity] = ("protein" if "polypeptide" in kind else
                          "dna" if kind == "polydeoxyribonucleotide" else
                          "rna" if kind == "polyribonucleotide" else "polymer")
    return result


def _token_map(block, length, metadata):
    chains, ids = metadata.get("token_chain_ids"), metadata.get("token_res_ids")
    if (not isinstance(chains, list) or not isinstance(ids, list)
            or len(chains) != length or len(ids) != length
            or any(not isinstance(chain, str) or not chain for chain in chains)
            or any(type(seq) is not int for seq in ids)):
        return [], "Invalid PAE token metadata. Linked selection is disabled."
    atoms = block.get_mmcif_category("_atom_site.")
    polymer_kinds = _polymer_kinds(block)
    groups, atom_records = {}, []
    first_model = _cell(atoms, "pdbx_PDB_model_num", 0, "1")
    for i in range(len(atoms.get("label_asym_id", []))):
        if _cell(atoms, "pdbx_PDB_model_num", i, "1") != first_model:
            continue
        chain = _cell(atoms, "label_asym_id", i)
        auth_chain = _cell(atoms, "auth_asym_id", i, chain)
        seq = _number(_cell(atoms, "label_seq_id", i))
        auth_seq = _cell(atoms, "auth_seq_id", i)
        ins = _cell(atoms, "pdbx_PDB_ins_code", i)
        comp = _cell(atoms, "label_comp_id", i, "UNK")
        key = (chain, seq, auth_chain, auth_seq, ins, comp)
        group = groups.setdefault(key, {
            "chain": chain, "seq": seq, "auth_chain": auth_chain, "auth_seq": auth_seq,
            "ins": ins, "comp": comp, "entity": _cell(atoms, "label_entity_id", i), "atoms": [],
        })
        record = {"name": _cell(atoms, "label_atom_id", i),
                  "element": _cell(atoms, "type_symbol", i).upper(),
                  "alt": _cell(atoms, "label_alt_id", i),
                  "bfactor": _cell(atoms, "B_iso_or_equiv", i),
                  "chain": chain, "auth_chain": auth_chain}
        atom_records.append(record)
        if record["element"] not in ("H", "D", "T"):
            group["atoms"].append(record)

    # JSON numbering can be author or label numbering. Never select an ambiguous
    # residue merely because one of the two namespaces happens to match first.
    lookup = defaultdict(set)
    for key, group in groups.items():
        for chain in (group["chain"], group["auth_chain"]):
            for seq in (group["seq"], _number(group["auth_seq"])):
                if seq is not None:
                    lookup[(chain, seq)].add(key)
    positions = defaultdict(list)
    for i, pair in enumerate(zip(chains, ids)):
        candidates = lookup.get(pair, set())
        if len(candidates) == 1:
            positions[next(iter(candidates))].append(i)

    # Repeated residue IDs denote atom tokens in AF3 ligands/modified residues.
    # Use CIF atom order only for matching AF3 atom metadata, not an arbitrary CIF.
    atom_chains = metadata.get("atom_chain_ids")
    ordered_atoms = (isinstance(atom_chains, list) and len(atom_chains) == len(atom_records)
                     and (atom_chains == [a["chain"] for a in atom_records]
                          or atom_chains == [a["auth_chain"] for a in atom_records]))
    plddts = metadata.get("atom_plddts")
    if ordered_atoms and plddts is not None:
        try:
            ordered_atoms = (len(plddts) == len(atom_records)
                             and all(abs(float(score) - float(atom["bfactor"])) <= .011
                                     for score, atom in zip(plddts, atom_records)))
        except (TypeError, ValueError, OverflowError):
            ordered_atoms = False

    result = [{"chain": chain, "auth_chain": chain, "seq": None, "auth_seq": str(seq),
               "ins": "", "entity": "", "comp": "?", "letter": "?", "display": "?",
               "kind": "unknown", "atom": "", "observed": False, "query": None,
               "reason": "Token has no unambiguous coordinate mapping"}
              for chain, seq in zip(chains, ids)]
    ion_elements = {"CA", "NA", "MG", "K", "ZN", "FE", "MN", "CU", "CO", "CL", "BR", "I", "NI", "CD"}
    for key, token_positions in positions.items():
        group = groups[key]
        records = group["atoms"]
        if not records:
            continue
        kind = polymer_kinds.get(group["entity"], "ligand")
        if kind == "ligand" and len(records) == 1 and records[0]["element"] in ion_elements:
            kind = "ion"
        atomic = len(token_positions) > 1 or kind in ("ion", "ligand")
        if atomic:
            if (len(token_positions) != len(records)
                    or len({a["name"] for a in records}) != len(records)
                    or any(a["alt"] for a in records)
                    or (len(records) > 1 and not ordered_atoms)):
                continue
        elif len(token_positions) != 1:
            continue
        query = {"label_asym_id": group["chain"], "label_comp_id": group["comp"]}
        if group["seq"] is not None:
            query["label_seq_id"] = group["seq"]
        elif _number(group["auth_seq"]) is not None:
            query["auth_seq_id"] = int(group["auth_seq"])
            if group["ins"]:
                query["pdbx_PDB_ins_code"] = group["ins"]
        else:
            continue
        for offset, position in enumerate(token_positions):
            atom = records[offset] if atomic else None
            selector = dict(query)
            if atom:
                selector["label_atom_id"] = [atom["name"]]
            letter = gemmi.find_tabulated_residue(group["comp"]).one_letter_code
            display = (atom["element"].capitalize() if kind == "ion" else
                       atom["name"] if atom else letter.upper() if letter.strip() else "X")
            result[position] = {key: value for key, value in group.items() if key != "atoms"}
            result[position].update(kind=kind, atom=atom["name"] if atom else "", display=display,
                                    letter=letter.upper() if letter.strip() else "X",
                                    observed=True, query=selector)
    missing = sum(not token["observed"] for token in result)
    note = (f"{missing} of {length} tokens could not be mapped unambiguously; "
            "only these tokens have structure linking disabled." if missing else "")
    return result, note


def residue_map(cif: bytes, length: int, metadata: dict | None = None) -> tuple[list[dict], str]:
    block = gemmi.cif.read_string(cif.decode()).sole_block()
    if metadata is not None and ("token_chain_ids" in metadata or "token_res_ids" in metadata):
        return _token_map(block, length, metadata)
    residues, note = _sequence_map(block, length)
    kinds = _polymer_kinds(block)
    for residue in residues:
        residue.update(kind=kinds.get(residue["entity"], "polymer"), atom="", display=residue["letter"],
                       query={"label_asym_id": residue["chain"], "label_seq_id": residue["seq"]})
    return residues, note


def _sequence_map(block, length):
    atoms = block.get_mmcif_category("_atom_site.")
    asym = block.get_mmcif_category("_struct_asym.")
    sequences = block.get_mmcif_category("_entity_poly_seq.")
    scheme = block.get_mmcif_category("_pdbx_poly_seq_scheme.")

    def value(table, key, index, default=""):
        column = table.get(key, [])
        item = column[index] if index < len(column) else None
        return default if item in (None, False, "", ".", "?") else str(item)

    def number(text):
        try:
            return int(text)
        except (ValueError, TypeError):
            return None

    entities = dict(zip(asym.get("id", []), asym.get("entity_id", [])))
    polymers = {}
    for i in range(len(sequences.get("entity_id", []))):
        entity = value(sequences, "entity_id", i)
        seq = number(value(sequences, "num", i))
        if seq is not None:
            # Microheterogeneous alternatives describe the same sequence position.
            polymers.setdefault(entity, {}).setdefault(seq, value(sequences, "mon_id", i, "UNK"))

    observed = {}
    chain_order = []
    first_model = value(atoms, "pdbx_PDB_model_num", 0, "1")
    for i in range(len(atoms.get("label_asym_id", []))):
        if value(atoms, "pdbx_PDB_model_num", i, "1") != first_model:
            continue
        chain = value(atoms, "label_asym_id", i)
        seq = number(value(atoms, "label_seq_id", i))
        # AF2/legacy fallback covers polymer residues only. AF3 uses token metadata.
        if not chain or seq is None:
            continue
        if chain not in observed:
            observed[chain] = {}
            chain_order.append(chain)
        observed[chain].setdefault(seq, {
            "auth_chain": value(atoms, "auth_asym_id", i, chain),
            "auth_seq": value(atoms, "auth_seq_id", i),
            "ins": value(atoms, "pdbx_PDB_ins_code", i),
            "comp": value(atoms, "label_comp_id", i, "UNK"),
        })
        entities.setdefault(chain, value(atoms, "label_entity_id", i))

    scheme_positions = {}
    for i in range(len(scheme.get("asym_id", []))):
        chain = value(scheme, "asym_id", i)
        seq = number(value(scheme, "seq_id", i))
        if not chain or seq is None:
            continue
        scheme_positions.setdefault(chain, {}).setdefault(seq, {
            "auth_chain": value(scheme, "pdb_strand_id", i, chain),
            "auth_seq": value(scheme, "auth_seq_num", i) or value(scheme, "pdb_seq_num", i),
            "ins": value(scheme, "pdb_ins_code", i),
            "comp": value(scheme, "mon_id", i, "UNK"),
        })
        entities.setdefault(chain, value(scheme, "entity_id", i))
    # Include sequence-only chains, even when all their coordinates are absent.
    for chain in list(entities) + list(scheme_positions):
        if chain not in chain_order and (entities.get(chain) in polymers or chain in scheme_positions):
            chain_order.append(chain)

    residues = []
    for chain in chain_order:
        entity = entities.get(chain, "")
        positions = scheme_positions.get(chain) or {
            seq: {"comp": comp} for seq, comp in polymers.get(entity, {}).items()
        }
        if not positions:
            positions = observed.get(chain, {})
            # Observed coordinates alone cannot account for sequence gaps.
            if sorted(positions) != list(range(1, len(positions) + 1)):
                return [], "Sequence numbering has gaps and the CIF has no complete sequence mapping. Linked selection is disabled."
        if set(observed.get(chain, {})) - set(positions):
            return [], "CIF sequence and coordinate numbering disagree. Linked selection is disabled."
        for seq in sorted(positions):
            item = {**positions[seq], **observed.get(chain, {}).get(seq, {})}
            comp = item.get("comp", "UNK")
            letter = gemmi.find_tabulated_residue(comp).one_letter_code
            residues.append({
                "chain": chain, "entity": entity, "seq": seq,
                "auth_chain": item.get("auth_chain", chain),
                "auth_seq": item.get("auth_seq", ""), "ins": item.get("ins", ""),
                "comp": comp, "letter": letter.upper() if letter.strip() else "X",
                "observed": seq in observed.get(chain, {}),
            })
    if len(residues) != length:
        return [], (f"PAE has {length} positions; the CIF sequence has {len(residues)}. "
                    "Linked selection is disabled to avoid selecting the wrong residues.")
    if not residues:
        return [], "No polymer residue mapping was found. Linked selection is disabled."
    note = ""
    if len(chain_order) > 1:
        note = ("Multi-chain mapping assumes the PAE uses CIF polymer chain order "
                f"({', '.join(chain_order)}). Check this order for externally supplied matrices.")
    return residues, note
