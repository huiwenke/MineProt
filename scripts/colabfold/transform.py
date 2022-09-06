import argparse
import os
import zipfile
import sys
import shutil
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "..")))
from RandomStr import RandomStr
from pdb2cif import pdb2cif

# List arguments
parser = argparse.ArgumentParser(description='Preprocess your ColabFold predictions for curation: pick out top-1 model and generate .cif for visualization.')
parser.add_argument('-i', type=str, help="Path to input folder. THIS ARGUMENT IS MANDATORY.")
parser.add_argument('-o', type=str, help="Path to output folder. THIS ARGUMENT IS MANDATORY.")
parser.add_argument('-n', type=int, default=0, help="Naming mode: 0: Use prefix; 1: Use name in .a3m; 2: Auto rename; 3: Customize name.")
parser.add_argument('-z', help="Unzip results.", action="store_true")
parser.add_argument('-r', help="Use relaxed results.", action="store_true")
parser.add_argument('--url', type=str, default="http://127.0.0.1/api/pdb2alphacif/", help="URL of PDB2CIF API.")

def CheckFileName(is_relaxed, file_name):
    """
    Pick out necessary files for curation.
    :param is_relaxed: Marks if the protein is relaxed, bool
    :param file_name: File name to be checked, str
    :return: Flag of whether the file name is valid, bool 
    """
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

def MakeTmp(is_zip, is_relaxed, file_name, input_dir, output_dir):
    """
    Copy files to temporary folder.
    :param is_zip: Marks if the file should be decompressed, bool
    :param is_relaxed: Marks if the protein is relaxed, bool
    :param input_dir: Copy source directory, str
    :param output_dir: Copy destination directory, str
    """
    file_path = os.path.join(input_dir, file_name)
    # Check if we need to decompress input file
    if is_zip and os.path.splitext(file_name)[-1] == ".zip":
        zip_file = zipfile.ZipFile(file_path)
        zip_list = zip_file.namelist()
        for zip_f in zip_list:
            # Check if the given file name is valid and decompress valid file to output directory
            if CheckFileName(is_relaxed, zip_f):
                zip_file.extract(zip_f, output_dir)
        zip_file.close()
    else:
        # Check if the given file name is valid and copy valid file to output directory
        if CheckFileName(is_relaxed, file_name):
            output_path = os.path.join(output_dir, file_name)
            shutil.copyfile(file_path, output_path)

def ReName(name_mode, file_name, input_dir):
    """
    Rename files and move them to output directory.
    :param name_mode: Renaming mode, int
    :param file_name: Original file name, str
    :param input_dir: Path to input directory, str
    :return: New file name, str
    """
    input_path = os.path.join(input_dir, file_name)
    prefix = os.path.splitext(file_name)[0]
    if name_mode == 0:
        # 0: Use prefix
        new_prefix = prefix
    elif name_mode == 1:
        # 1: Use name in .a3m
        with open(input_path, 'r') as f:
            new_prefix = f.readlines()[1][1:-1]
    elif name_mode == 2:
        # 2: Auto rename
        new_prefix = "MP_" + RandomStr(10)
    else:
        # 3: Customize name with user input
        print("Please enter a name:")
        new_prefix = input()
    return new_prefix

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
TmpDir = "MP-Temp-" + RandomStr(10)
print("Using temporary folder: "+TmpDir)
os.makedirs(TmpDir)

# Copy source file(s) to temp directory
for file_name in os.listdir(InputDir):
    MakeTmp(args.z, args.r, file_name, InputDir, TmpDir)

# Enumerate A3M files and rename with renaming mode. Then move them to output directory.
NameList = []
TmpList = os.listdir(TmpDir)
TmpList.sort()
for file_name in TmpList:
    file_path = os.path.join(TmpDir, file_name)
    if os.path.splitext(file_name)[-1] == ".a3m":
        NameList.append(ReName(args.n, file_name, TmpDir))
    output_path = os.path.join(OutputDir, NameList[-1]) + os.path.splitext(file_name)[-1]
    shutil.move(file_path, output_path)

# Delete temp directory
shutil.rmtree(TmpDir)

# Convert PDF to CIF
print("Generating CIF files...")
for prefix in NameList:
    pdb2cif(OutputDir, prefix, args.url)

# All done
print("Done.")