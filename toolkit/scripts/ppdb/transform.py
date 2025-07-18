import argparse
import os
import sys
import json
import multiprocessing
from functools import partial
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "..")))
from api import pdb2cif

# Argument definitions
parser = argparse.ArgumentParser(description='Preprocess predicted PDB files for curation.')
parser.add_argument('-i', type=str, required=True, help="Path to input folder. THIS ARGUMENT IS MANDATORY.")
parser.add_argument('-o', type=str, help="Path to output folder.")
parser.add_argument('-t', '--threads', type=int, default=1, 
                    help="Number of parallel processes to use for PDB processing. Default: 1")
parser.add_argument('--url', type=str, default="http://127.0.0.1/api/pdb2alphacif/", 
                    help="URL of PDB2CIF API.")

def FixPDB(pdb_path):
    """
    Process a PDB file to calculate average pLDDT scores per residue.
    Returns modified PDB content and JSON score data.
    """
    ans = ["", ""]
    plddt = []
    with open(pdb_path, 'r') as f:
        for line in f:
            if line[0:4] == "ATOM":
                aa_id = int(line[22:26])-1
                if len(plddt) == aa_id:
                    plddt.append([])
                plddt[aa_id].append(float(line[60:66]))
    score = {"plddt":[0]*len(plddt)}
    with open(pdb_path, 'r') as f:
        for line in f:
            if line[0:4] == "ATOM":
                aa_id = int(line[22:26])-1
                score["plddt"][aa_id] = round(sum(plddt[aa_id])/len(plddt[aa_id]),2)
                line = line[:60] + str(score["plddt"][aa_id]).rjust(6) + line[66:]
            ans[0] += line
    ans[1] = json.dumps(score)
    #print(pdb_path, sum(score["plddt"])/len(score["plddt"]), sep='\t')
    return ans

def process_single_file(file_name, InputDir, OutputDir):
    """Process a single PDB file and write output files."""
    prefix = os.path.splitext(file_name)[0]
    input_pdb_path = os.path.join(InputDir, file_name)
    try:
        [pdb_text, json_text] = FixPDB(input_pdb_path)
    except Exception as e:
        print(f"Error processing {file_name}: {str(e)}")
        return None
    
    output_pdb_path = os.path.join(OutputDir, file_name)
    with open(output_pdb_path, 'w') as f_pdb:
        f_pdb.write(pdb_text)
    
    output_json_path = os.path.join(OutputDir, prefix + '.json')
    with open(output_json_path, 'w') as f_json:
        f_json.write(json_text)
    
    return prefix

def main():
    # Parse arguments
    args = parser.parse_args()
    InputDir = args.i
    if not args.o:
        print("Output parameter -o is unset, using default value (same path as -i).")
        args.o = args.i
    OutputDir = args.o
    num_processes = max(1, args.threads)  # Ensure at least 1 process

    print(f"Data will be processed from {InputDir} to {OutputDir}")
    print(f"Using {num_processes} parallel process(es) for PDB processing")
    if not os.path.exists(OutputDir):
        print(f"Output directory {OutputDir} does not exist. Creating...")
        os.makedirs(OutputDir)

    # Process PDB files with multiprocessing
    file_list = os.listdir(InputDir)
    pdb_files = [f for f in file_list if f.endswith(".pdb")]
    NameList = []

    # Create processing function with fixed parameters
    process_func = partial(process_single_file, 
                          InputDir=InputDir, 
                          OutputDir=OutputDir)
    
    # Use multiprocessing Pool for parallel execution
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.map(process_func, pdb_files)
    
    # Collect successful results
    for res in results:
        if res is not None:
            NameList.append(res)

    # Convert PDB to CIF (single-threaded)
    print("Generating CIF files...")
    for prefix in NameList:
        pdb2cif(OutputDir, prefix, args.url)

    # All done
    print("Processing complete.")

if __name__ == "__main__":
    main()