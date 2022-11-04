import requests
import json

def GetUniProtKB(accession):
    """
    Get annotations from UniProt API (Proteins service).
    :param accession: Candidate UniProt accession, str
    :return: JSON response from UniProt API, obj
    """
    headers = {'Accept': 'application/json'}
    request_url = "https://www.ebi.ac.uk/proteins/api/proteins/"+accession
    retry = 0
    while retry < 3:
        try:
            response = requests.get(url=request_url, headers=headers, timeout=10)
            return response
        except:
            retry += 1

def GetUniParc(upi):
    """
    Get annotations from UniProt API (UniParc service).
    :param upi: Candidate UniParc identifier, str
    :return: JSON response from UniProt API, obj
    """
    headers = {'Accept': 'application/json'}
    request_url = "https://www.ebi.ac.uk/proteins/api/uniparc/upi/"+upi+"?rfDdtype=RefSeq"
    retry = 0
    while retry < 3:
        try:
            response = requests.get(url=request_url, headers=headers, timeout=10)
            return response
        except:
            retry += 1

def UniProt2MineProt(identifier_list):
    """
    Find the first annotated homolog in candidate list
    :param identifier_list: Candidate homolog list, list
    :return: Formatted annotations, dict
    """
    result_json = {
        "homolog": "",
        "database": "",
        "description": []
    }
    for identifier in identifier_list:
        accession = identifier.split()[0]
        if accession[0]=='>':
            accession = accession[1:]
        if accession[0:3] in ["sp|", "tr|"]:
            accession = accession.split('|')[1]
        response = GetUniProtKB(accession)
        if response.status_code == 200:
            response_json = json.loads(response.text)
            result_json["homolog"] = response_json["accession"]
            try:
                result_json["description"].append(response_json["protein"]["submittedName"][0]["fullName"]["value"])
            except:
                result_json["description"].append(response_json["protein"]["recommendedName"]["fullName"]["value"])
            result_json["database"] = "uniprotkb"
            result_json["description"].append(response_json["accession"])
            for dbReference in response_json["dbReferences"]:
                if dbReference["type"] == "GO":
                    result_json["description"].append(dbReference["id"])
                    result_json["description"].append(dbReference["properties"]["term"])
                if dbReference["type"] == "InterPro":
                    result_json["description"].append(dbReference["id"])
                    result_json["description"].append(dbReference["properties"]["entry name"])
            break
        response = GetUniParc(accession)
        if response.status_code == 200:
            response_json = json.loads(response.text)
            try:
                for property in response_json["dbReference"][0]["property"]:
                    if property["type"] == "protein_name":
                        result_json["homolog"] = response_json["accession"]
                        result_json["database"] = "uniparc"
                        result_json["description"].append(property["value"])
                        break
                result_json["description"].append(response_json["dbReference"][0]["id"])
                result_json["description"].append(response_json["accession"])
                for signatureSequenceMatch in response_json["signatureSequenceMatch"]:
                    if "ipr" in signatureSequenceMatch:
                        result_json["description"].append(signatureSequenceMatch["ipr"]["id"])
                        result_json["description"].append(signatureSequenceMatch["ipr"]["name"])
                break
            except:
                continue
    return result_json