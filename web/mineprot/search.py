import hashlib
import json
from urllib.parse import quote

import httpx

from . import settings
from .storage import atomic_write, component, inside, protein_names, repo_file


def es_request(method: str, path: str, **kwargs) -> httpx.Response:
    with httpx.Client(timeout=30, trust_env=False) as client:
        response = client.request(method, settings.ES_URL + "/" + path, **kwargs)
    if response.status_code >= 500:
        raise RuntimeError("Elasticsearch is unavailable")
    return response


def datasets() -> list[str]:
    if not settings.REPO_ROOT.is_dir():
        return []
    response = es_request("GET", "_cat/indices", params={"format": "json", "h": "index"})
    response.raise_for_status()
    indexes = {item["index"] for item in response.json()}
    return sorted(path.name for path in settings.REPO_ROOT.iterdir()
                  if path.is_dir() and path.name in indexes)


def search(repos: list[str], term: str) -> list[dict]:
    if not repos:
        return []
    index = ",".join(quote(component(repo), safe="*") for repo in repos)
    response = es_request("POST", index + "/_search", json={
        "query": {"match_phrase": {"anno.description": term}}, "size": 200})
    if response.status_code == 404:
        return []
    response.raise_for_status()
    return response.json().get("hits", {}).get("hits", [])


def get_document(repo: str, document_id: str) -> dict:
    response = es_request("GET", quote(component(repo), safe="") + "/_doc/" + quote(document_id, safe=""))
    if response.status_code == 404:
        return {}
    response.raise_for_status()
    return response.json().get("_source", {})


def browse_cache(repo: str, sort: str) -> list[dict]:
    component(repo)
    directory = inside(settings.REPO_ROOT, repo)
    names = protein_names(repo)
    fingerprint = []
    for path in sorted(directory.iterdir()):
        if path.is_file():
            stat = path.stat()
            fingerprint.append((path.name, stat.st_size, stat.st_mtime_ns))
    key = hashlib.sha256(json.dumps(fingerprint).encode()).hexdigest()
    prefix = "MP_BROWSE_" + hashlib.sha256(repo.encode()).hexdigest() + "_"
    cache = settings.CACHE_ROOT / (prefix + key + "_" + sort + ".json")
    if cache.is_file():
        return json.loads(cache.read_text())
    import base64
    rows = []
    for name in names:
        source = get_document(repo, base64.b64encode(name.encode()).decode())
        annotation = source.get("anno") or {}
        score = source.get("score", -1)
        descriptions = annotation.get("description") or []
        rows.append({"name": name, "repo": repo, "plddt": score,
                     "homolog": annotation.get("homolog", ""),
                     "database": annotation.get("database", ""),
                     "anno": descriptions[0] if descriptions else "",
                     "has_a3m": repo_file(repo, name + ".a3m").is_file()
                     or repo_file(repo, name + ".a3m.gz").is_file()})
    rows.sort(key=(lambda row: (-float(row["plddt"] or -1), row["name"]))
              if sort == "plddt" else lambda row: row["name"])
    atomic_write(cache, json.dumps(rows).encode())
    return rows


def clear_browse(repo: str) -> None:
    component(repo)
    prefix = "MP_BROWSE_" + hashlib.sha256(repo.encode()).hexdigest() + "_"
    for path in settings.CACHE_ROOT.glob(prefix + "*.json"):
        path.unlink(missing_ok=True)
