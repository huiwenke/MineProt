import argparse
import os
import sys
import json
import base64
sys.path.append(os.path.abspath(os.path.dirname(sys.argv[0])))
from annotate import UniProt2MineProt
import api

# List arguments
parser = argparse.ArgumentParser(description='Import your proteins into Elasticsearch.')
parser.add_argument('-i', type=str, help="Path to your preprocessed A3M files. THIS ARGUMENT IS MANDATORY.")
parser.add_argument('-n', type=str, help="Elasticsearch index name.")
parser.add_argument('-a', help="Annotate proteins using UniProt API.", action="store_true")
parser.add_argument('-f', help="Force overwrite.", action="store_true")
parser.add_argument('--url', type=str, default="http://127.0.0.1/api/es", help="URL of MineProt Elasticsearch API.")

# Now parse user-given arguments
args = parser.parse_args()
# Mandatory argument -i, configures input directory
InputDir = args.i
print("Will import proteins stored in "+InputDir)
# If Elasticsearch index name is not specified, use InputDir instead
if not args.n:
    args.n = os.path.basename(args.i)
print("Proteins will be imported to "+args.n)
# If argument -f is specified as TRUE, reset the Elasticsearch index
if args.f:
    print("WARNING: ALL DATA IN "+args.n+" WILL BE OVERWRITTEN.")
    api.EsDel(args.url, args.n)
# If argument -a is specified as TRUE, try to annotate proteins using UniProt API when importing.
if args.a:
    print("Proteins will be annotated using UniProt API.")

# Start importing
print("Importing proteins to Elasticsearch...")
# Enumerate all files in InputDir
for file_name in os.listdir(InputDir):
    # Generate JSON from A3M file, and then POST to Elasticsearch
    if os.path.splitext(file_name)[-1] == ".a3m":
        es_request_json = {
            "name": "",
            "seq": "",
            "score": -1.0,
            "anno": {
                "homolog": "",
                "database": "",
                "description": []
            }
        }
        es_request_json["name"] = os.path.splitext(file_name)[0]
        es_id = str(base64.b64encode(os.path.splitext(file_name)[0].encode("utf-8")),"utf-8")
        response_json = json.loads(api.EsGet(args.url, args.n, es_id).text)
        # Check if the current protein is already stored in Elasticsearch
        if "error" not in response_json and response_json["found"]:
            # Simply skip current protein if it has been stored previously
            print("Skipping "+es_request_json["name"]+"...")
            continue
        else:
            # Execute the import
            print("Importing "+es_request_json["name"]+"...")
        # Generate file path and open the file
        file_path = os.path.join(InputDir, file_name)
        with open(file_path,'r') as fi:
            try:
                # Calculate average pLDDT
                with open(os.path.join(InputDir, es_request_json["name"])+".json", 'r') as f_json:
                    score_plddt = json.load(f_json)["plddt"]
                    es_request_json["score"] = sum(score_plddt)/len(score_plddt)
                # Read MSA from file
                lines = fi.readlines()
                es_request_json["seq"] = lines[2][1:-1]
                # Check if we need to annotate proteins and annotate
                if args.a:
                    es_request_json["anno"] = UniProt2MineProt(lines[3::2])
                    if es_request_json["anno"]["homolog"]=="":
                        print("Warning: Failed to find annotation for "+es_request_json["name"]+".")
                api.EsAdd(args.url, args.n, es_id, json.dumps(es_request_json))
            except:
                print("Error: Failed to import "+es_request_json["name"]+".")

# All done
print("Done.")