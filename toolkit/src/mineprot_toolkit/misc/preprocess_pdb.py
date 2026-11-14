import argparse
import json
import multiprocessing
import os
from functools import partial

from mineprot_toolkit.common.api import pdb2cif
from mineprot_toolkit.common.defaults import CONVERSION_URL


# Argument definitions
def build_parser():
    parser = argparse.ArgumentParser(description="Preprocess predicted PDB files for curation.")
    parser.add_argument(
        "-i", type=str, required=True, help="Path to input folder. THIS ARGUMENT IS MANDATORY."
    )
    parser.add_argument("-o", type=str, help="Path to output folder.")
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=1,
        help="Number of parallel processes to use for PDB processing. Default: 1",
    )
    parser.add_argument("--url", type=str, default=CONVERSION_URL, help="URL of PDB2CIF API.")
    return parser


def normalize_pdb_scores(pdb_path):
    """
    Process a PDB file to calculate average pLDDT scores per residue.
    Returns modified PDB content and JSON score data.
    """
    ans = ["", ""]
    plddt = []
    with open(pdb_path, "r") as f:
        for line in f:
            if line[0:4] == "ATOM":
                aa_id = int(line[22:26]) - 1
                if len(plddt) == aa_id:
                    plddt.append([])
                plddt[aa_id].append(float(line[60:66]))
    score = {"plddt": [0] * len(plddt)}
    with open(pdb_path, "r") as f:
        for line in f:
            if line[0:4] == "ATOM":
                aa_id = int(line[22:26]) - 1
                score["plddt"][aa_id] = round(sum(plddt[aa_id]) / len(plddt[aa_id]), 2)
                line = line[:60] + str(score["plddt"][aa_id]).rjust(6) + line[66:]
            ans[0] += line
    ans[1] = json.dumps(score)
    # print(pdb_path, sum(score["plddt"])/len(score["plddt"]), sep='\t')
    return ans


def process_single_file(file_name, input_dir, output_dir):
    """Process a single PDB file and write output files."""
    prefix = os.path.splitext(file_name)[0]
    input_pdb_path = os.path.join(input_dir, file_name)
    try:
        [pdb_text, json_text] = normalize_pdb_scores(input_pdb_path)
    except Exception as e:
        print(f"Error processing {file_name}: {str(e)}")
        return None

    output_pdb_path = os.path.join(output_dir, file_name)
    with open(output_pdb_path, "w") as f_pdb:
        f_pdb.write(pdb_text)

    output_json_path = os.path.join(output_dir, prefix + ".json")
    with open(output_json_path, "w") as f_json:
        f_json.write(json_text)

    return prefix


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    input_dir = args.i
    if not args.o:
        print("Output parameter -o is unset, using default value (same path as -i).")
        args.o = args.i
    output_dir = args.o
    num_processes = max(1, args.threads)  # Ensure at least 1 process

    print(f"Data will be processed from {input_dir} to {output_dir}")
    print(f"Using {num_processes} parallel process(es) for PDB processing")
    if not os.path.exists(output_dir):
        print(f"Output directory {output_dir} does not exist. Creating...")
        os.makedirs(output_dir)

    # Process PDB files with multiprocessing
    file_list = os.listdir(input_dir)
    pdb_files = [f for f in file_list if f.endswith(".pdb")]
    name_list = []

    # Create processing function with fixed parameters
    process_func = partial(process_single_file, input_dir=input_dir, output_dir=output_dir)

    # Use multiprocessing Pool for parallel execution
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.map(process_func, pdb_files)

    # Collect successful results
    for res in results:
        if res is not None:
            name_list.append(res)

    # Convert PDB to CIF (single-threaded)
    print("Generating CIF files...")
    for prefix in name_list:
        pdb2cif(output_dir, prefix, args.url)

    # All done
    print("Processing complete.")


if __name__ == "__main__":
    main()
