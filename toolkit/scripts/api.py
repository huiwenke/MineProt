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

def EsAdd(url, repo, id, data):
    headers = {'Content-Type': 'application/json'}
    request_url = '/'.join([url, repo, "add", id])
    retry = 0
    while retry < 3:
        try:
            reponse = requests.post(url=request_url, headers=headers, data=data, timeout=10)
            return reponse
        except:
            retry += 1

def EsDel(url, repo):
    request_url = '/'.join([url, repo, "del", ''])
    retry = 0
    while retry < 3:
        try:
            reponse = requests.post(url=request_url, timeout=10)
            return reponse
        except:
            retry += 1

def EsGet(url, repo, id):
    request_url = '/'.join([url, repo, "get", id])
    retry = 0
    while retry < 3:
        try:
            reponse = requests.post(url=request_url, timeout=10)
            return reponse
        except:
            retry += 1

def Check(url, params):
    retry = 0
    while retry < 3:
        try:
            reponse = requests.get(url=url+"check.php", params=params, timeout=10)
            return reponse
        except:
            retry += 1

def Import(url, data):
    headers = {
        'Content-Type': 'application/json',
        'Accept-encoding': 'gzip'
    }
    retry = 0
    while retry < 3:
        try:
            reponse = requests.post(url=url, headers=headers, data=data, timeout=10)
            return reponse
        except:
            retry += 1