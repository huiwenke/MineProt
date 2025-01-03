import argparse
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "..")))
from api import pdb2cif

# List arguments
parser = argparse.ArgumentParser(description='Preprocess your predicted PDB files for curation.')
parser.add_argument('-i', type=str, help="Path to input folder. THIS ARGUMENT IS MANDATORY.")
parser.add_argument('-o', type=str, help="Path to output folder.")
parser.add_argument('--url', type=str, default="http://127.0.0.1/api/pdb2alphacif/", help="URL of PDB2CIF API.")

# Parse arguments
args = parser.parse_args()
InputDir = args.i
if not args.o:
    print("Output parameter -o is unset, using default value (same path as -i).")
    args.o = args.i
OutputDir = args.o
print("Data will be generated in "+OutputDir)
if not os.path.exists(OutputDir):
    print("Output directory "+OutputDir+" not exist. Creating ...")
    os.makedirs(OutputDir)

NameList = []
file_list = os.listdir(InputDir)
for file_name in file_list:
    if os.path.splitext(file_name)[-1] == ".pdb":
        NameList.append(os.path.splitext(file_name)[0])

# Convert PDB to CIF
print("Generating CIF files...")
for prefix in NameList:
    pdb2cif(OutputDir, prefix, args.url)

# All done
print("Done.")