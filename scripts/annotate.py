import requests

def GetUniProt(accession):
    headers = {'Content-Type': 'application/json'}
    request_url = "https://www.ebi.ac.uk/proteins/api/proteins/"+accession
    response = requests.get(url=request_url, headers=headers)
    return response
