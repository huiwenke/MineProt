import argparse
import os
import requests
import json
import base64
import gzip

parser = argparse.ArgumentParser(
    description='Import your proteins into repository.')
parser.add_argument('-n', type=str, help="Repository name.")
parser.add_argument('-i', type=str, help="Path to your preprocessed files (A3M, PDB, CIF & JSON).")
parser.add_argument('-f', help="Force overwrite.", action="store_true")
parser.add_argument('--url', type=str, default="http://127.0.0.1/api/import2repo/", help="URL of MineProt API.")

args = parser.parse_args()
InputDir = args.i
if not args.n:
    args.n = os.path.basename(args.i)
print("Importing proteins to repository "+args.n+"...")

for file_name in os.listdir(InputDir):
    import_request_json = {
        "name": file_name,
        "repo": args.n,
        "text": "",
        "force": args.f
    }
    headers = {
        'Content-Type': 'application/json',
        'Accept-encoding': 'gzip'
    }
    file_path = os.path.join(InputDir, file_name)
    with open(file_path, 'r') as fi:
        import_request_json["text"] = str(base64.b64encode(fi.read().encode("utf-8")), "utf-8")
    response = requests.post(url=args.url, headers=headers, data=gzip.compress(json.dumps(import_request_json).encode())).text
    print(response+' '+import_request_json["repo"]+'/'+import_request_json["name"])

print("Done.")
