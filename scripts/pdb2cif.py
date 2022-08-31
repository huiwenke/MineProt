import requests
import json
import base64
import os

def pdb2cif(data_dir, protein_name, request_url):
    output_path = os.path.join(data_dir, protein_name)
    try:
        request_json = {
            "name": protein_name,
            "data": ""
        }
        headers = {'Content-Type': 'application/json'}
        with open(output_path+".pdb",'r') as fi, open(output_path+".cif",'w') as fo:
            request_json["data"] = str(base64.b64encode(fi.read().encode("utf-8")),"utf-8")
            response = requests.post(url=request_url, headers=headers, data=json.dumps(request_json))
            fo.write(response.text)
    except:
        print("Prediction of "+protein_name+" failed. Please check out.")