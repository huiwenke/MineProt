import argparse
import os
import sys
import shutil
import json
import pickle
from tempfile import TemporaryDirectory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "..")))
from pdb2cif import pdb2cif
from rename import ReName

# List arguments
parser = argparse.ArgumentParser(description='Preprocess your AlphaFold predictions for curation: pick out top-1 model and generate .cif for visualization.')
parser.add_argument('-i', type=str, help="Path to input folder. THIS ARGUMENT IS MANDATORY.")
parser.add_argument('-o', type=str, help="Path to output folder. THIS ARGUMENT IS MANDATORY.")
parser.add_argument('-n', type=int, default=0, help="Naming mode: 0: Use prefix; 1: Use name in .a3m; 2: Auto rename; 3: Customize name.")
parser.add_argument('--url', type=str, default="http://127.0.0.1/api/pdb2alphacif/", help="URL of PDB2CIF API.")


def MakeTmp(dir_name, input_dir, output_dir):
    """
    Copy files to temporary folder.
    :param input_dir: Copy source directory, str
    :param output_dir: Copy destination directory, str
    """
    file_name = dir_name
    output_path = os.path.join(output_dir, file_name)
    try:
        dir_path = os.path.join(input_dir, dir_name)
        with open(dir_path+"/ranking_debug.json", 'r') as fin_json:
            ranked_0 = json.load(fin_json)["order"][0]
    except:
        print("Error: Prediction of "+dir_name+" failed.")
        return
    pkl_path = dir_path+"/result_"+ranked_0+".pkl"
    pkl_data = pickle.load(open(pkl_path, 'rb'))
    json_data = {"plddt": pkl_data["plddt"].tolist(), "pae": [], "max_pae": 31.75, "ptm": 0}
    try:
        json_data["pae"] = pkl_data["predicted_aligned_error"].tolist()
        json_data["max_pae"] = float(pkl_data["max_predicted_aligned_error"])
        json_data["ptm"] = float(pkl_data["ptm"])
    except:
        print("Warining: Not pTM model. PAE plot will be disabled.")
    with open(output_path+".json", 'w') as fout_json:
        json.dump(json_data, fout_json)
    shutil.copyfile(dir_path+"/ranked_0.pdb", output_path+".pdb")
    with open(dir_path+"/msas/bfd_uniclust_hits.a3m", 'r') as fin_a3m, open(output_path+".a3m", 'w') as fout_a3m:
        fout_a3m.write("# Added by MineProt toolkit\n")
        fout_a3m.write(fin_a3m.read())

# Parse arguments
args = parser.parse_args()
InputDir = args.i
OutputDir = args.o
print("Data will be copied from "+InputDir+" to "+OutputDir)
if not os.path.exists(OutputDir):
    print("Output directory "+OutputDir+" not exist. Creating ...")
    os.makedirs(OutputDir)
if not args.n:
    print("Naming mode parameter -n is unset, using default value (0: Use prefix).")
    args.n = 0

# Create temp directory
TmpDir = TemporaryDirectory(prefix="MP-Temp-").name
print("Using temporary folder: "+TmpDir)
os.makedirs(TmpDir)

# Copy source file(s) to temp directory
for dir_name in os.listdir(InputDir):
    MakeTmp(dir_name, InputDir, TmpDir)

# Enumerate files and rename with renaming mode. Then move them to output directory.
NameList = []
TmpList = os.listdir(TmpDir)
TmpList.sort()
for file_name in TmpList:
    file_path = os.path.join(TmpDir, file_name)
    if os.path.splitext(file_name)[-1] == ".a3m":
        NameList.append(ReName(args.n, file_name, TmpDir))
    output_path = os.path.join(
        OutputDir, NameList[-1]) + os.path.splitext(file_name)[-1]
    print("Moving "+file_path+" to "+output_path+"...")
    shutil.move(file_path, output_path)

# Delete temp directory
shutil.rmtree(TmpDir)

# Convert PDF to CIF
print("Generating CIF files...")
for prefix in NameList:
    pdb2cif(OutputDir, prefix, args.url)

# All done
print("Done.")
