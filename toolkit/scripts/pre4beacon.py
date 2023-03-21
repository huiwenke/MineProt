import argparse
import os
import time
import sys
import shutil
import json
import threading
sys.path.append(os.path.abspath(os.path.dirname(sys.argv[0])))
from annotate import Make3bMeta

# List arguments
parser = argparse.ArgumentParser(description='Prepare metadata for 3D-Beacons client.')
parser.add_argument('-i', type=str, help="Path to your MineProt repo. THIS ARGUMENT IS MANDATORY.")
parser.add_argument('-o', type=str, help="Path to your data directory for 3D-Beacons. THIS ARGUMENT IS MANDATORY.")
parser.add_argument('-t', type=int, default=1, help="Threads to use.")
parser.add_argument('--max-msa', dest="max_msa", type=int, default=50, help="Max number of msas to use for mapping.")

# Now parse user-given arguments
args = parser.parse_args()
Max_MSA = args.max_msa
# Mandatory argument -i, configures input directory
InputDir = args.i
print("Will use proteins stored in "+InputDir)
# Mandatory argument -o, configures output directory
# mkdir -p ./data/{pdb,cif,metadata,index}
OutputDir = args.o
if not os.path.exists(OutputDir):
    os.makedirs(OutputDir)
DirPDB = os.path.join(OutputDir, "pdb")
if not os.path.exists(DirPDB):
    os.makedirs(DirPDB)
DirMetadata = os.path.join(OutputDir, "metadata")
if not os.path.exists(DirMetadata):
    os.makedirs(DirMetadata)
DirCIF = os.path.join(OutputDir, "cif")
if not os.path.exists(DirCIF):
    os.makedirs(DirCIF)
DirIndex = os.path.join(OutputDir, "index")
if not os.path.exists(DirIndex):
    os.makedirs(DirIndex)

def worker(semaphore, file_name):
    file_path = os.path.join(InputDir, file_name)
    createdDate = time.strftime("%Y-%m-%d", time.localtime(os.path.getctime(file_path)))
    output_path = os.path.join(DirPDB, file_name)
    protein = os.path.splitext(file_name)[0]
    with open(os.path.join(InputDir, protein)+".json", 'r') as fin_json:
        score_plddt = json.load(fin_json)["plddt"]
        confidenceAvgLocalScore = sum(score_plddt)/len(score_plddt)
    with open(os.path.join(InputDir, protein)+".a3m", 'r') as f_a3m:
        lines = f_a3m.readlines()
        seq = lines[2][:-1]
        metadata_json = Make3bMeta(seq, confidenceAvgLocalScore, createdDate, lines[3::2], Max_MSA)
        if metadata_json["mappingAccession"] != "":
            print(protein+": "+metadata_json["mappingAccession"])
            shutil.copyfile(file_path, output_path)
            with open(os.path.join(DirMetadata, protein)+".json", 'w') as fout_json:
                json.dump(metadata_json, fout_json)
        else:
            print("Error: Failed to find mappingAccession for "+protein+".")
    semaphore.release()

semaphore = threading.Semaphore(args.t)
threads = []
# Start importing
print("Prepare metadata for 3D-Beacons...")
# Enumerate all files in InputDir
for file_name in os.listdir(InputDir):
    if os.path.splitext(file_name)[-1] == ".pdb":
        semaphore.acquire()
        t = threading.Thread(target=worker, args=(semaphore, file_name))
        threads.append(t)
        t.start()
for t in threads:
    t.join()

# All done
print("Done.")