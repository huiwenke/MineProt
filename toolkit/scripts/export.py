import argparse
import os
import json
import requests
import base64

# List arguments
parser = argparse.ArgumentParser(description='Export data from MineProt Search Page.')
parser.add_argument("url", type=str, nargs='+', help="Search URL. THIS ARGUMENT IS MANDATORY.")
parser.add_argument('-o', type=str, default="./MineProt_Search_Results", help="Path to output folder.")

args = parser.parse_args()
OutputDir = args.o
if not os.path.exists(OutputDir):
    print("Output directory "+OutputDir+" not exist. Creating ...")
    os.makedirs(OutputDir)

Search_URL = args.url[0]
MineProt_URL = Search_URL.split("/search.php")[0]
reponse = requests.get(Search_URL)
Search_Results = json.loads(base64.b64decode(reponse.text.split("|JSON|")[1]))
with open(os.path.join(OutputDir, "result.json"), 'w') as fout_json:
    fout_json.write(json.dumps(Search_Results))
for search_result in Search_Results:
    repo = search_result["_index"]
    repo_path = os.path.join(OutputDir, repo)
    if not os.path.exists(repo_path):
        os.makedirs(repo_path)
    protein = search_result["_source"]["name"]
    for suffix in [".pdb",".cif",".json",".a3m"]:
        reponse = requests.get(MineProt_URL+"/repo/"+repo+'/'+protein+suffix)
        if reponse.status_code == 200:
            with open(os.path.join(repo_path, protein+suffix), 'w') as fo:
                fo.write(reponse.text)
        reponse = requests.get(MineProt_URL+"/repo/"+repo+'/'+protein+suffix+'.gz')
        if reponse.status_code == 200:
            with open(os.path.join(repo_path, protein+suffix), 'wb') as fo:
                fo.write(reponse.text)
