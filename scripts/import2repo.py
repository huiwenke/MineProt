import argparse
import os
import requests
import json
import base64
import gzip

# List arguments
parser = argparse.ArgumentParser(description='Import your proteins into repository.')
parser.add_argument('-i', type=str, help="Path to your preprocessed files (A3M, PDB, CIF & JSON). THIS ARGUMENT IS MANDATORY.")
parser.add_argument('-n', type=str, help="Local repository name.")
parser.add_argument('-f', help="Force overwrite.", action="store_true")
parser.add_argument('--url', type=str, default="http://127.0.0.1/api/import2repo/", help="URL of MineProt API.")

# Now parse user-given arguments
args = parser.parse_args()
# Mandatory argument -i, configures input directory
InputDir = args.i
print("Will import proteins stored in "+InputDir)
# If local repository path is not specified, use InputDir instead
if not args.n:
    args.n = os.path.basename(args.i)

# Start importing
print("Importing proteins to local repository "+args.n+"...")

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
    # Open file and encode file data with BASE64
    file_path = os.path.join(InputDir, file_name)
    with open(file_path, 'r') as fi:
        import_request_json["text"] = str(base64.b64encode(fi.read().encode("utf-8")), "utf-8")
    # POST to MineProt Import API
    response = requests.post(url=args.url, headers=headers, data=gzip.compress(json.dumps(import_request_json).encode())).text
    print(response+' '+import_request_json["repo"]+'/'+import_request_json["name"])

# All done
print("Done.")
