def pdb2seq(pdb_file):
    """Convert a PDB file to a FASTA sequence"""
    seq = ""
    id = 0
    with open(pdb_file, "r") as f:
        for line in f:
            if line.startswith("ATOM"):
                residue = line[17:20].strip()
                if id != int(line[22:26].strip()):
                    id = int(line[22:26].strip())
                    seq += amino_acid_code(residue)

    # return the sequence as a FASTA string
    return seq

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
        "VAL": "V"
    }
    return code_map[residue]