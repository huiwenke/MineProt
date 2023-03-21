import requests
import json
from Bio.Align import PairwiseAligner
from Bio.Align import substitution_matrices
from Bio.Seq import Seq


def GetUniProtKB(accession):
    """
    Get annotations from UniProt API (Proteins service).
    :param accession: Candidate UniProt accession, str
    :return: JSON response from UniProt API, obj
    """
    headers = {"Accept": "application/json"}
    request_url = "https://www.ebi.ac.uk/proteins/api/proteins/" + accession
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
    headers = {"Accept": "application/json"}
    request_url = (
        "https://www.ebi.ac.uk/proteins/api/uniparc/upi/" + upi + "?rfDdtype=RefSeq"
    )
    retry = 0
    while retry < 3:
        try:
            response = requests.get(url=request_url, headers=headers, timeout=10)
            return response
        except:
            retry += 1


def FixAccession(identifier):
    """
    Fix A3M identifier to legal accession
    :param identifier: Input identifier, str
    :return: Fixed accession, str
    """
    accession = identifier.split()[0]
    if accession[0] == ">":
        accession = accession[1:]
    if accession[0:3] in ["sp|", "tr|"]:
        accession = accession.split("|")[1]
    if "UniRef100_" in accession:
        accession = accession.split("_")[1]
    return accession


def UniProt2MineProt(identifier_list, max_msa):
    """
    Find the first annotated homolog in candidate list
    :param identifier_list: Candidate homolog list, list
    :param max_msa: Max number of candidate msas to use for annotation, int
    :return: Formatted annotations, dict
    """
    result_json = {"homolog": "", "database": "", "description": []}
    identifier_num = max_msa
    for identifier in identifier_list:
        identifier_num -= 1
        if identifier_num < 0:
            break
        accession = FixAccession(identifier)
        response = GetUniProtKB(accession)
        if response.status_code == 200:
            response_json = json.loads(response.text)
            result_json["homolog"] = response_json["accession"]
            try:
                result_json["description"].append(
                    response_json["protein"]["submittedName"][0]["fullName"]["value"]
                )
            except:
                result_json["description"].append(
                    response_json["protein"]["recommendedName"]["fullName"]["value"]
                )
            result_json["database"] = "uniprotkb"
            result_json["description"].append(response_json["accession"])
            for dbReference in response_json["dbReferences"]:
                if dbReference["type"] == "GO":
                    result_json["description"].append(dbReference["id"])
                    result_json["description"].append(dbReference["properties"]["term"])
                if dbReference["type"] == "InterPro":
                    result_json["description"].append(dbReference["id"])
                    result_json["description"].append(
                        dbReference["properties"]["entry name"]
                    )
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
                        result_json["description"].append(
                            signatureSequenceMatch["ipr"]["id"]
                        )
                        result_json["description"].append(
                            signatureSequenceMatch["ipr"]["name"]
                        )
                break
            except:
                continue
    return result_json


def Align(seq1, seq2):
    aligner = PairwiseAligner()
    aligner.mode = "local"
    aligner.substitution_matrix = substitution_matrices.load("BLOSUM62")
    aligner.gap_score = -10
    aligner.extend_gap_score = -0.5
    alignments = aligner.align(seq1, seq2)
    alignment = alignments[0]
    start = alignment.aligned[0][0][0] + 1
    end = alignment.aligned[0][-1][1] + 1
    sequenceIdentity = str(alignment).count("|") / alignment.shape[1] * 100
    coverage = (end - start + 1) / len(seq1)
    return {
        "start": int(start),
        "end": int(end),
        "sequenceIdentity": float(sequenceIdentity),
        "coverage": float(coverage),
        "alignment": alignment,
    }


def Make3bMeta(seq, confidenceAvgLocalScore, createdDate, identifier_list, max_msa):
    """
    Generate metadata for 3D-Beacons client
    :param seq: Sequence, str
    :param identifier_list: Candidate UniProt homolog list, list
    :param max_msa: Max number of candidate msas to use for annotation, int
    :return: Metadata, json
    """
    result_json = {
        "mappingAccession": "",
        "mappingAccessionType": "uniprot",
        "start": 0,
        "end": 0,
        "modelCategory": "Ab initio",
        "modelType": "single",
        "confidenceType": "pLDDT",
        "confidenceAvgLocalScore": confidenceAvgLocalScore,
        "createdDate": createdDate,
        "sequenceIdentity": 0.0,
        "coverage": 0.0,
    }
    identifier_num = max_msa
    for identifier in identifier_list:
        identifier_num -= 1
        if identifier_num < 0:
            break
        accession = FixAccession(identifier)
        response = GetUniProtKB(accession)
        if response.status_code == 200:
            response_json = json.loads(response.text)
            if "gene" not in response_json:
                continue
            align_json = Align(Seq(response_json["sequence"]["sequence"]), Seq(seq))
            result_json["mappingAccession"] = accession
            result_json["start"] = align_json["start"]
            result_json["end"] = align_json["end"]
            result_json["sequenceIdentity"] = align_json["sequenceIdentity"]
            result_json["coverage"] = align_json["coverage"]
            break
    return result_json
