"""Gemmi conversions, including the bundled PDBe Mol* 1.2.1 AF2 contract.

No Gemmi source is copied or modified. Its MPL-2.0 license is independent
of the MIT license applying to this application module.
"""
import math
import re

import gemmi


_L_AMINO_ACIDS = frozenset(
    "ALA ARG ASN ASP CYS GLN GLU HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL".split())


def _repair_component_types(block):
    """Fill missing standard residue types without reclassifying ligands."""
    components = block.get_mmcif_category("_chem_comp.")
    ids = components.get("id", [])
    if not ids:
        return
    types = components.get("type", [None] * len(ids))
    changed = False
    for i, component in enumerate(ids):
        if types[i] not in (None, False, "", ".", "?"):
            continue
        component = component.upper()
        if component in _L_AMINO_ACIDS:
            types[i] = "L-peptide linking"
        elif component == "GLY":
            types[i] = "peptide linking"
        elif component in ("A", "C", "G", "U", "I"):
            types[i] = "RNA linking"
        elif component in ("DA", "DC", "DG", "DT", "DI", "DU"):
            types[i] = "DNA linking"
        else:
            continue
        changed = True
    if changed:
        components["type"] = types
        block.set_mmcif_category("_chem_comp.", components)


def _remove_local_database_marker(block):
    """Undo our old marker: Mol* mistakes its presence for a PDB archive."""
    databases = block.get_mmcif_category("_database_2.")
    ids = databases.get("database_id", [])
    keep = [i for i, value in enumerate(ids) if value != "MineProt"]
    if len(keep) == len(ids):
        return
    # Erase the category entirely when no genuine database records remain.
    if keep:
        block.set_mmcif_category("_database_2.", {
            key: [values[i] for i in keep] for key, values in databases.items()
        })
    else:
        block.find_mmcif_category("_database_2.").erase()


def pdb_to_alphacif(data: bytes, name: str = "model") -> str:
    structure = gemmi.read_pdb_string(data.decode("utf-8"))
    if not len(structure) or not any(len(chain) for chain in structure[0]):
        raise ValueError("PDB contains no residues")
    structure.name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    structure.setup_entities()
    # AF2 PDBs often have no SEQRES. Supply the observed sequence per entity,
    # without inventing coordinates for residues absent from the input.
    for entity in structure.entities:
        if entity.entity_type != gemmi.EntityType.Polymer or entity.full_sequence:
            continue
        for chain in structure[0]:
            residues = [res for res in chain if res.subchain in entity.subchains]
            if residues:
                entity.full_sequence = [res.name for res in residues]
                break
    structure.assign_label_seq_id()
    document = structure.make_mmcif_document()
    block = document.sole_block()
    # alphafoldView explicitly attaches the confidence theme. No database_2
    # marker is needed; adding one disables Mol*'s automatic DSSP selection.
    _repair_component_types(block)
    # The legacy toolkit explicitly checks for this canonical sequence field.
    # Write it even when an upstream writer omits it from an otherwise valid CIF.
    polymers = block.get_mmcif_category("_entity_poly.")
    if polymers:
        entities = {entity.name: entity for entity in structure.entities}
        canonical = []
        for entity_id in polymers["entity_id"]:
            entity = entities.get(entity_id)
            sequence = entity.full_sequence if entity is not None else []
            letters = [gemmi.find_tabulated_residue(comp).one_letter_code for comp in sequence]
            canonical.append("".join(letter.upper() if letter.strip() else "X" for letter in letters))
        existing = polymers.get("pdbx_seq_one_letter_code_can", [])
        polymers["pdbx_seq_one_letter_code_can"] = [
            existing[i] if i < len(existing) and existing[i] else sequence
            for i, sequence in enumerate(canonical)]
        block.set_mmcif_category("_entity_poly.", polymers)
    # Keep a deterministic numeric entity ID for the legacy confidence reader,
    # which hardcodes entity "1". Other entities retain distinct numeric IDs.
    entity_ids = list(block.find_values("_entity.id"))
    mapping = {old: str(i + 1) for i, old in enumerate(entity_ids)}
    for tag in ("_entity.id", "_entity_poly.entity_id", "_entity_poly_seq.entity_id",
                "_struct_asym.entity_id", "_atom_site.label_entity_id"):
        values = block.find_values(tag)
        for i in range(len(values)):
            values[i] = mapping.get(values[i], values[i])

    metrics = block.init_loop("_ma_qa_metric.", ["id", "name", "type", "mode"])
    metrics.add_row(["2", "pLDDT", "pLDDT", "local"])
    local = block.init_loop("_ma_qa_metric_local.", [
        "label_asym_id", "label_comp_id", "label_seq_id", "metric_id",
        "metric_value", "model_id", "ordinal_id"])
    ordinal = 0
    for model_index, model in enumerate(structure, 1):
        model_id = str(getattr(model, "num", model_index))
        for chain in model:
            for residue in chain:
                if residue.entity_type != gemmi.EntityType.Polymer or residue.label_seq is None:
                    continue
                atoms = list(residue)
                if not atoms:
                    continue
                ca = next((atom for atom in atoms if atom.name == "CA"), atoms[0])
                score = float(ca.b_iso)
                if not math.isfinite(score) or not 0 <= score <= 100:
                    raise ValueError("AF2 pLDDT must be between 0 and 100")
                ordinal += 1
                local.add_row([gemmi.cif.quote(residue.subchain), gemmi.cif.quote(residue.name),
                               str(residue.label_seq), "2", str(score), model_id, str(ordinal)])
    if not ordinal:
        raise ValueError("PDB contains no polymer confidence scores")
    # Do not silently rewrite original author numbering. The legacy viewer uses
    # auth_seq_id to look up the local table's label_seq_id: see viewer_cif().
    return document.as_string()


def cif_to_pdb(data: bytes) -> str:
    document = gemmi.cif.read_string(data.decode("utf-8"))
    structure = gemmi.make_structure_from_block(document.sole_block())
    if not len(structure):
        raise ValueError("CIF contains no models")
    # Gemmi raises for chain identifiers the PDB format cannot represent.
    return structure.make_pdb_string()


def viewer_cif(data: bytes) -> bytes:
    """Adapt only single-entity predicted CIFs for the unchanged old viewer.

    Raw /repo downloads and conversion results keep author numbering. Multiple
    polymer entities cannot be made fully colorable by the old reader without
    changing its JavaScript, so those files are returned intact.
    """
    document = gemmi.cif.read_string(data.decode("utf-8"))
    block = document.sole_block()
    _repair_component_types(block)
    _remove_local_database_marker(block)
    if not len(block.find_values("_ma_qa_metric_local.metric_value")):
        return document.as_string().encode()
    polymer_ids = list(block.find_values("_entity_poly.entity_id"))
    if len(set(polymer_ids)) != 1:
        return document.as_string().encode()
    polymer_id = polymer_ids[0]
    # Preserve non-polymer entity identities while assigning polymer entity 1.
    ids = list(block.find_values("_entity.id"))
    mapping = {polymer_id: "1"}
    mapping.update({value: str(i + 2) for i, value in enumerate(v for v in ids if v != polymer_id)})
    for tag in ("_entity.id", "_entity_poly.entity_id", "_entity_poly_seq.entity_id",
                "_struct_asym.entity_id", "_atom_site.label_entity_id"):
        values = block.find_values(tag)
        for i in range(len(values)):
            values[i] = mapping.get(values[i], values[i])
    labels = block.find_values("_atom_site.label_seq_id")
    authors = block.find_values("_atom_site.auth_seq_id")
    insertions = block.find_values("_atom_site.pdbx_PDB_ins_code")
    for i in range(min(len(labels), len(authors))):
        if labels[i] not in (".", "?"):
            authors[i] = labels[i]
            if len(insertions) > i:
                insertions[i] = "?"
    return document.as_string().encode()
