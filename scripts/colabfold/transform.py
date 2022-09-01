import argparse
import os
import zipfile
import sys
import shutil
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "..")))
from RandomStr import RandomStr
from pdb2cif import pdb2cif

parser = argparse.ArgumentParser(description='Preprocess your ColabFold predictions for curation: pick out top-1 model and generate .cif for visualization.')
parser.add_argument('-n', type=int, default=0, help="0: Use prefix; 1: Use name in .a3m; 2: Auto rename; 3: Customize name.")
parser.add_argument('-z', help="Unzip results.", action="store_true")
parser.add_argument('-r', help="Use relaxed results.", action="store_true")
parser.add_argument('-i', type=str, help="Path to input folder.")
parser.add_argument('-o', type=str, help="Path to output folder.")
parser.add_argument('--url', type=str, default="http://127.0.0.1/api/pdb2alphacif/", help="URL of PDB2CIF API.")

# Pick out necessary files for curation.
def CheckFileName(is_relaxed, file_name):
    suffix = os.path.splitext(file_name)[-1]
    if suffix == ".a3m":
        return True
    if suffix == ".pdb":
        if is_relaxed:
            return file_name.count("_relaxed_rank_1_")
        else:
            return file_name.count("_unrelaxed_rank_1_")
    if suffix == ".json":
        return file_name.count("_unrelaxed_rank_1_")
    return False

# Copy files to temporary folder.
def MakeTmp(is_zip, is_relaxed, file_name, input_dir, output_dir):
    file_path = os.path.join(input_dir, file_name)
    if is_zip and os.path.splitext(file_name)[-1] == ".zip":
        zip_file = zipfile.ZipFile(file_path)
        zip_list = zip_file.namelist()
        for zip_f in zip_list:
            if CheckFileName(is_relaxed, zip_f):
                zip_file.extract(zip_f, output_dir)
        zip_file.close()
    else:
        if CheckFileName(is_relaxed, file_name):
            output_path = os.path.join(output_dir, file_name)
            shutil.copyfile(file_path, output_path)

# Rename files and move them to output folder.
def ReName(name_mode, file_name, input_dir):
    input_path = os.path.join(input_dir, file_name)
    prefix = os.path.splitext(file_name)[0]
    if name_mode == 0:
        new_prefix = prefix
    elif name_mode == 1:
        with open(input_path, 'r') as f:
            new_prefix = f.readlines()[1][1:-1]
    elif name_mode == 2:
        new_prefix = "MP_" + RandomStr(10)
    else:
        print("Please enter a name:")
        new_prefix = input()
    return new_prefix

args = parser.parse_args()
InputDir = args.i
OutputDir = args.o
if not os.path.exists(OutputDir):
    os.makedirs(OutputDir)
if not args.n:
    args.n = 0

TmpDir = "/tmp/MP-Temp-" + RandomStr(10)
print("Temporary folder: "+TmpDir)
os.makedirs(TmpDir)
for file_name in os.listdir(InputDir):
    MakeTmp(args.z, args.r, file_name, InputDir, TmpDir)
NameList = []
TmpList = os.listdir(TmpDir)
TmpList.sort()
for file_name in TmpList:
    file_path = os.path.join(TmpDir, file_name)
    if os.path.splitext(file_name)[-1] == ".a3m":
        NameList.append(ReName(args.n, file_name, TmpDir))
    output_path = os.path.join(OutputDir, NameList[-1]) + os.path.splitext(file_name)[-1]
    shutil.move(file_path, output_path)
shutil.rmtree(TmpDir)

print("Generating CIF files...")
for prefix in NameList:
    pdb2cif(OutputDir, prefix, args.url)

print("Done.")