from .structures import load_structure, protein_residues


def structure_sequence(structure):
    """Join amino-acid residues across first-model chains in structure order."""
    import gemmi

    residues = protein_residues(structure)
    if not residues:
        raise ValueError("No amino-acid residues found in the structure")
    return "".join(
        gemmi.find_tabulated_residue(residue.name).one_letter_code.upper() for residue in residues
    )


def pdb2seq(pdb_file):
    """Read a protein sequence, also accepting CIF and FCZ structures."""
    structure, _ = load_structure(pdb_file)
    return structure_sequence(structure)


def amino_acid_code(residue):
    """Map a three-letter amino acid code to a one-letter code"""
    code_map = {
        "ALA": "A",
        "ARG": "R",
        "ASN": "N",
        "ASP": "D",
        "CYS": "C",
        "GLN": "Q",
        "GLU": "E",
        "GLY": "G",
        "HIS": "H",
        "ILE": "I",
        "LEU": "L",
        "LYS": "K",
        "MET": "M",
        "PHE": "F",
        "PRO": "P",
        "SER": "S",
        "THR": "T",
        "TRP": "W",
        "TYR": "Y",
        "VAL": "V",
    }
    return code_map[residue]
