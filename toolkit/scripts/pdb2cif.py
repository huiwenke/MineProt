import requests
import json
import base64
import os

def pdb2cif(data_dir, protein_name, request_url):
    """
    Convert PDB-formatted file to CIF-formatted file.
    Result CIF file will be output to input directory.
    :param data_dir: Path to PDB file, str
    :param protein_name: Protein name of corresponding PDB file, str
    :param request_url: URL of MineProt PDB-CIF Converting API, str
    """
    output_path = os.path.join(data_dir, protein_name)
    if os.path.exists(output_path+".cif"):
        print("Skipping "+protein_name+"...")
        return
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
        print("Error: Prediction of "+protein_name+" failed.")