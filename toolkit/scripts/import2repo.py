import argparse
import os
import requests
import json
import hashlib
import base64
import gzip

# List arguments
parser = argparse.ArgumentParser(description='Import your proteins into repository.')
parser.add_argument('-i', type=str, help="Path to your preprocessed files (A3M, PDB, CIF & JSON). THIS ARGUMENT IS MANDATORY.")
parser.add_argument('-n', type=str, help="MineProt repository name.")
parser.add_argument('-f', help="Force overwrite.", action="store_true")
parser.add_argument('--url', type=str, default="http://127.0.0.1/api/import2repo/", help="URL of MineProt import2repo API.")

# Now parse user-given arguments
args = parser.parse_args()
# Mandatory argument -i, configures input directory
InputDir = args.i
print("Will import proteins stored in "+InputDir)
# If MineProt repository path is not specified, use InputDir instead
if not args.n:
    args.n = os.path.basename(args.i)

# Start importing
print("Importing proteins to MineProt repository "+args.n+"...")

# Enumerate all files in InputDir
for file_name in os.listdir(InputDir):
    # Generate JSON from files, and then POST to MineProt Import API
    import_request_json = {
        "name": file_name,
        "repo": args.n,
        "text": "",
        "force": args.f
    }
    # Compress the JSON with gzip
    headers = {
        'Content-Type': 'application/json',
        'Accept-encoding': 'gzip'
    }
    file_path = os.path.join(InputDir, file_name)
    with open(file_path, 'r') as fi:
        file_text = fi.read().encode("utf-8")
        if requests.get(url=args.url+"check.php", params=import_request_json).text == hashlib.md5(file_text).hexdigest():
            print("Skipping "+import_request_json["repo"]+'/'+import_request_json["name"])
            continue
    # Encode file data with BASE64
    import_request_json["text"] = str(base64.b64encode(file_text), "utf-8")
    # POST to MineProt Import API
    response = requests.post(url=args.url, headers=headers, data=gzip.compress(json.dumps(import_request_json).encode()))
    if response.status_code == 200:
        print(response.text+' '+import_request_json["repo"]+'/'+import_request_json["name"])
    else:
        print("Error "+str(response.status_code)+": Failed to import "+import_request_json["repo"]+'/'+import_request_json["name"])

# All done
print("Done.")
