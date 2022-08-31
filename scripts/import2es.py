import argparse
import os
import sys
import requests
import json
import base64
sys.path.append(os.path.abspath(os.path.dirname(sys.argv[0])))
from annotate import GetUniProt

parser = argparse.ArgumentParser(description='Import your proteins into Elasticsearch.')
parser.add_argument('-n', type=str, help="Name Elasticsearch index.")
parser.add_argument('-i', type=str, help="Path to your preprocessed files, including .a3m, .pdb & .json.")
parser.add_argument('-a', help="Annotate proteins with UniProt API.", action="store_true")
parser.add_argument('--url', type=str, default="http://127.0.0.1/api/es", help="URL of MineProt API.")

args = parser.parse_args()
InputDir = args.i
if not args.n:
    args.n = os.path.basename(args.i)
for file_name in os.listdir(InputDir):
    if os.path.splitext(file_name)[-1] == ".a3m":
        es_request_json = {
            "name": "",
            "seq": "",
            "anno": {
                "homolog": "",
                "description": []
            }
        }
        file_path = os.path.join(InputDir, file_name)
        es_request_json["name"] = os.path.splitext(file_name)[0]
        with open(file_path,'r') as fi:
            lines = fi.readlines()
            headers = {'Content-Type': 'application/json'}
            es_request_json["seq"] = lines[2][1:-1]
            if args.a:
                identifier_list = lines[3::2]
                for identifier in identifier_list:
                    accession = identifier[1:].split()[0]
                    response = GetUniProt(accession)
                    if response.status_code == 200:
                        response_json = json.loads(response.text)
                        es_request_json["anno"]["homolog"] = response_json["accession"]
                        try:
                            es_request_json["anno"]["description"].append(response_json["protein"]["submittedName"][0]["fullName"]["value"])
                        except:
                            es_request_json["anno"]["description"].append(response_json["protein"]["recommendedName"]["fullName"]["value"])
                        for dbReference in response_json["dbReferences"]:
                            if dbReference["type"] == "GO":
                                es_request_json["anno"]["description"].append(dbReference["id"])
                                es_request_json["anno"]["description"].append(dbReference["properties"]["term"])
                            if dbReference["type"] == "InterPro":
                                es_request_json["anno"]["description"].append(dbReference["id"])
                                es_request_json["anno"]["description"].append(dbReference["properties"]["entry name"])
                        break
            es_id = str(base64.b64encode(es_request_json["name"].encode("utf-8")),"utf-8")
            request_url = '/'.join([args.url, args.n, "add", es_id])
            requests.post(url=request_url, headers=headers, data=json.dumps(es_request_json))

                    