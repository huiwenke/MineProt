import argparse
import os
import sys
import requests
import json
import base64
sys.path.append(os.path.abspath(os.path.dirname(sys.argv[0])))
from annotate import UniProt2MineProt

parser = argparse.ArgumentParser(description='Import your proteins into Elasticsearch.')
parser.add_argument('-n', type=str, help="Name Elasticsearch index.")
parser.add_argument('-i', type=str, help="Path to your preprocessed files, including .a3m, .pdb and .json.")
parser.add_argument('-a', help="Annotate proteins using UniProt API.", action="store_true")
parser.add_argument('-f', help="Force overwrite.", action="store_true")
parser.add_argument('--url', type=str, default="http://127.0.0.1/api/es", help="URL of MineProt API.")

args = parser.parse_args()
InputDir = args.i
if not args.n:
    args.n = os.path.basename(args.i)
print("Exporting proteins to Elasticsearch...")
if args.f:
    request_url = '/'.join([args.url, args.n, "del", ''])
    print("Overwritting "+args.n+"...")
    requests.post(request_url)
if args.a:
    print("Annotating proteins using UniProt API...")

for file_name in os.listdir(InputDir):
    headers = {'Content-Type': 'application/json'}
    if os.path.splitext(file_name)[-1] == ".a3m":
        es_request_json = {
            "name": "",
            "seq": "",
            "anno": {
                "homolog": "",
                "description": []
            }
        }
        es_request_json["name"] = os.path.splitext(file_name)[0]
        es_id = str(base64.b64encode(os.path.splitext(file_name)[0].encode("utf-8")),"utf-8")
        request_url = '/'.join([args.url, args.n, "get", es_id])
        response_json = json.loads(requests.post(url=request_url, headers=headers).text)
        if "error" not in response_json and response_json["found"]:
            print("Skipping "+es_request_json["name"]+"...")
            continue
        else:
            print("Exporting "+es_request_json["name"]+"...")
        file_path = os.path.join(InputDir, file_name)
        with open(file_path,'r') as fi:
            try:
                lines = fi.readlines()
                es_request_json["seq"] = lines[2][1:-1]
                if args.a:
                    es_request_json["anno"] = UniProt2MineProt(lines[3::2])
                    if es_request_json["anno"]["homolog"]=="":
                        print("Warning: Failed to find annotation for "+es_request_json["name"]+".")
                request_url = '/'.join([args.url, args.n, "add", es_id])
                requests.post(url=request_url, headers=headers, data=json.dumps(es_request_json))
            except:
                print("Error: Failed to import "+es_request_json["name"]+".")
print("Done.")