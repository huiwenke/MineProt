import argparse
import os
import sys
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "..")))
from api import pdb2cif

# List arguments
parser = argparse.ArgumentParser(description='Preprocess your predicted PDB files for curation.')
parser.add_argument('-i', type=str, help="Path to input folder. THIS ARGUMENT IS MANDATORY.")
parser.add_argument('-o', type=str, help="Path to output folder.")
parser.add_argument('--url', type=str, default="http://127.0.0.1/api/pdb2alphacif/", help="URL of PDB2CIF API.")

def FixPDB(pdb_path):
    ans = ["",""]
    plddt = []
    with open(pdb_path, 'r') as f:
        for line in f:
            if line[0:4] == "ATOM":
                aa_id = int(line[22:26])-1
                if len(plddt)==aa_id:
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
    print(pdb_path, sum(score["plddt"])/len(score["plddt"]), sep='\t')
    return ans

# Parse arguments
args = parser.parse_args()
InputDir = args.i
if not args.o:
    print("Output parameter -o is unset, using default value (same path as -i).")
    args.o = args.i
OutputDir = args.o
print("Data will be copied from "+InputDir+" to "+OutputDir)
if not os.path.exists(OutputDir):
    print("Output directory "+OutputDir+" not exist. Creating ...")
    os.makedirs(OutputDir)

NameList = []
file_list = os.listdir(InputDir)
for file_name in file_list:
    if os.path.splitext(file_name)[-1] == ".pdb":
        NameList.append(os.path.splitext(file_name)[0])
        input_pdb_path = os.path.join(InputDir, file_name)
        [pdb_text, json_text] = FixPDB(input_pdb_path)
        output_pdb_path = os.path.join(OutputDir, file_name)
        with open(output_pdb_path, 'w') as f_pdb:
            f_pdb.write(pdb_text)
        output_json_path = os.path.join(OutputDir, NameList[-1]+'.json')
        with open(output_json_path, 'w') as f_json:
            f_json.write(json_text)

# Convert PDB to CIF
print("Generating CIF files...")
for prefix in NameList:
    pdb2cif(OutputDir, prefix, args.url)

# All done
print("Done.")