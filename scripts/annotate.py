import requests
import json

def GetUniProt(accession):
    """
    Get annotations from UniProt API.
    :param accession: Candidate UniProt accession, str
    :return: JSON response from UniProt API, obj
    """
    headers = {'Content-Type': 'application/json'}
    request_url = "https://www.ebi.ac.uk/proteins/api/proteins/"+accession
    response = requests.get(url=request_url, headers=headers)
    return response

def UniProt2MineProt(identifier_list):
    """
    Find the first annotated homolog in candidate list
    :param identifier_list: Candidate homolog list, list
    :return: Formatted annotations, dict
    """
    result_json = {
        "homolog": "",
        "description": []
    }
    for identifier in identifier_list:
        accession = identifier.split()[0]
        if accession[0]=='>':
            accession = accession[1:]
        if accession[0:3] in ["sp|", "tr|"]:
            accession = accession.split('|')[1]
        response = GetUniProt(accession)
        if response.status_code == 200:
            response_json = json.loads(response.text)
            result_json["homolog"] = response_json["accession"]
            try:
                result_json["description"].append(response_json["protein"]["submittedName"][0]["fullName"]["value"])
            except:
                result_json["description"].append(response_json["protein"]["recommendedName"]["fullName"]["value"])
            for dbReference in response_json["dbReferences"]:
                if dbReference["type"] == "GO":
                    result_json["description"].append(dbReference["id"])
                    result_json["description"].append(dbReference["properties"]["term"])
                if dbReference["type"] == "InterPro":
                    result_json["description"].append(dbReference["id"])
                    result_json["description"].append(dbReference["properties"]["entry name"])
            break
    return result_json