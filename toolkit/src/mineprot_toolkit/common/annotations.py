import json

import requests
from Bio.Align import PairwiseAligner, substitution_matrices
from Bio.Seq import Seq


def get_uniprotkb(accession):
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
        except Exception:
            retry += 1


def get_uniparc(upi):
    """
    Get annotations from UniProt API (UniParc service).
    :param upi: Candidate UniParc identifier, str
    :return: JSON response from UniProt API, obj
    """
    headers = {"Accept": "application/json"}
    request_url = "https://www.ebi.ac.uk/proteins/api/uniparc/upi/" + upi + "?rfDdtype=RefSeq"
    retry = 0
    while retry < 3:
        try:
            response = requests.get(url=request_url, headers=headers, timeout=10)
            return response
        except Exception:
            retry += 1


def get_afdb(accession):
    """
    Get annotations from AFDB API.
    :param accession: Candidate UniProt accession, str
    :return: JSON response from AFDB API, obj
    """
    headers = {"Accept": "application/json"}
    request_url = "https://alphafold.com/api/prediction/" + accession
    retry = 0
    while retry < 3:
        try:
            response = requests.get(url=request_url, headers=headers, timeout=10)
            return response
        except Exception:
            retry += 1


def fix_accession(identifier):
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
    if accession[0:3] in ["AF-"]:
        accession = accession.split("-")[1]
    if "UniRef100_" in accession:
        accession = accession.split("_")[1]
    return accession


def uniprot_to_mineprot(identifier_list, max_msa):
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
        accession = fix_accession(identifier)
        response = get_uniprotkb(accession)
        if response.status_code == 200:
            response_json = json.loads(response.text)
            result_json["homolog"] = response_json["accession"]
            try:
                result_json["description"].append(
                    response_json["protein"]["submittedName"][0]["fullName"]["value"]
                )
            except Exception:
                result_json["description"].append(
                    response_json["protein"]["recommendedName"]["fullName"]["value"]
                )
            result_json["database"] = "uniprotkb"
            result_json["description"].append(response_json["accession"])
            for db_reference in response_json["dbReferences"]:
                if db_reference["type"] == "GO":
                    result_json["description"].append(db_reference["id"])
                    result_json["description"].append(db_reference["properties"]["term"])
                if db_reference["type"] == "InterPro":
                    result_json["description"].append(db_reference["id"])
                    result_json["description"].append(db_reference["properties"]["entry name"])
            break
        response = get_uniparc(accession)
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
                for signature_sequence_match in response_json["signatureSequenceMatch"]:
                    if "ipr" in signature_sequence_match:
                        result_json["description"].append(signature_sequence_match["ipr"]["id"])
                        result_json["description"].append(signature_sequence_match["ipr"]["name"])
                break
            except Exception:
                continue
    return result_json


def afdb_to_mineprot(identifier_list):
    """
    Find the first annotated homolog in candidate list
    :param identifier_list: Candidate homolog list, list
    :param max_msa: Max number of candidate msas to use for annotation, int
    :return: Formatted annotations, dict
    """
    result_json = {"homolog": "", "database": "", "description": []}
    for identifier in identifier_list:
        accession = fix_accession(identifier)
        response = get_afdb(accession)
        if response.status_code == 200:
            response_json = json.loads(response.text)
            result_json["homolog"] = response_json[0]["uniprotAccession"]
            result_json["description"].append(response_json[0]["uniprotDescription"])
            result_json["database"] = "afdb"
            break
    return result_json


def align_sequences(seq1, seq2):
    aligner = PairwiseAligner()
    aligner.mode = "local"
    aligner.substitution_matrix = substitution_matrices.load("BLOSUM62")
    aligner.gap_score = -10
    aligner.extend_gap_score = -0.5
    alignments = aligner.align(seq1, seq2)
    alignment = alignments[0]
    start = alignment.aligned[0][0][0] + 1
    end = alignment.aligned[0][-1][1] + 1
    sequence_identity = str(alignment).count("|") / alignment.shape[1] * 100
    coverage = (end - start + 1) / len(seq1)
    return {
        "start": int(start),
        "end": int(end),
        "sequenceIdentity": float(sequence_identity),
        "coverage": float(coverage),
        "alignment": alignment,
    }


def make_beacon_metadata(seq, confidence_avg_local_score, created_date, identifier_list, max_msa):
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
        "confidenceAvgLocalScore": confidence_avg_local_score,
        "createdDate": created_date,
        "sequenceIdentity": 0.0,
        "coverage": 0.0,
    }
    identifier_num = max_msa
    for identifier in identifier_list:
        identifier_num -= 1
        if identifier_num < 0:
            break
        accession = fix_accession(identifier)
        response = get_uniprotkb(accession)
        if response.status_code == 200:
            response_json = json.loads(response.text)
            if "gene" not in response_json:
                continue
            align_json = align_sequences(Seq(response_json["sequence"]["sequence"]), Seq(seq))
            result_json["mappingAccession"] = accession
            result_json["start"] = align_json["start"]
            result_json["end"] = align_json["end"]
            result_json["sequenceIdentity"] = align_json["sequenceIdentity"]
            result_json["coverage"] = align_json["coverage"]
            break
    return result_json
