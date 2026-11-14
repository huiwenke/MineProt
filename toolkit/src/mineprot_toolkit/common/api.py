"""HTTP helpers used by system-specific preprocessing and metadata imports."""

import base64
from pathlib import Path
from urllib.parse import quote

from .uploads import session


def pdb2cif(data_dir, protein_name, request_url):
    """Convert a local PDB through MineProt, writing only a successful CIF response."""
    output = Path(data_dir) / (protein_name + ".cif")
    if output.exists():
        print(f"Skipping {protein_name}...")
        return
    data = output.with_suffix(".pdb").read_bytes()
    response = session().post(
        request_url,
        json={
            "name": protein_name,
            "data": base64.b64encode(data).decode(),
        },
        timeout=(10, 300),
    )
    response.raise_for_status()
    if "_entity_poly.pdbx_seq_one_letter_code_can" not in response.text:
        raise ValueError(f"Invalid CIF response for {protein_name}")
    output.write_text(response.text)


def es_request(url, repo, action, document_id="", **kwargs):
    endpoint = "/".join(
        [url.rstrip("/"), quote(repo, safe=""), action, quote(document_id, safe="")]
    )
    response = session().post(endpoint, timeout=(10, 30), **kwargs)
    # Missing documents/indices are expected while checking or resetting an import.
    if not (response.status_code == 404 and action in ("get", "del")):
        response.raise_for_status()
    return response


def es_add(url, repo, document_id, data):
    return es_request(
        url, repo, "add", document_id, data=data, headers={"Content-Type": "application/json"}
    )


def es_delete(url, repo):
    return es_request(url, repo, "del")


def es_get(url, repo, document_id):
    return es_request(url, repo, "get", document_id)
