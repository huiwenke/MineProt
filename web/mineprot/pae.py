"""Map PAE sequence positions to mmCIF label numbering for Mol*."""
import gemmi


def residue_map(cif: bytes, length: int) -> tuple[list[dict], str]:
    block = gemmi.cif.read_string(cif.decode()).sole_block()
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
        # Ligands/water have no label_seq_id and never consume a PAE position.
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
