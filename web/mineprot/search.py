import base64
import hashlib
import json
import time
from urllib.parse import quote

import httpx

from . import settings
from .storage import atomic_write, component, inside, protein_names, repo_file


def es_request(method: str, path: str, *, client: httpx.Client | None = None, **kwargs) -> httpx.Response:
    if client is None:
        with httpx.Client(timeout=30, trust_env=False) as connection:
            response = connection.request(method, settings.ES_URL + "/" + path, **kwargs)
    else:
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
    directory_mtime = directory.stat().st_mtime_ns
    sort = "plddt" if sort == "plddt" else "name"
    prefix = "MP_BROWSE_" + hashlib.sha256(repo.encode()).hexdigest() + "_"
    cache = settings.CACHE_ROOT / (prefix + "v2_" + sort + ".json")
    if cache.is_file():
        cached = json.loads(cache.read_text())
        # API writes invalidate explicitly; directory changes invalidate immediately.
        # Bound freshness for edits made directly to existing files or ES documents.
        if (cached["directory_mtime"] == directory_mtime
                and 0 <= time.time() - cached["created"] < 300):
            return cached["rows"]
    names = protein_names(repo)
    sources = {}
    with httpx.Client(timeout=30, trust_env=False) as client:
        for offset in range(0, len(names), 500):
            batch = names[offset:offset + 500]
            response = es_request("POST", quote(repo, safe="") + "/_mget", client=client,
                                  params={"_source_includes": "score,anno"},
                                  json={"ids": [base64.b64encode(name.encode()).decode() for name in batch]})
            if response.status_code == 404:
                continue
            response.raise_for_status()
            documents = response.json().get("docs", [])
            if len(documents) != len(batch):
                raise RuntimeError("Incomplete Elasticsearch browse response")
            for name, document in zip(batch, documents):
                error = document.get("error")
                if error and error.get("type") != "index_not_found_exception":
                    raise RuntimeError(f"Cannot read browse metadata for {repo}/{name}: {error}")
                sources[name] = document.get("_source") or {}
    rows = []
    for name in names:
        source = sources.get(name, {})
        annotation = source.get("anno") or {}
        score = source.get("score", -1)
        descriptions = annotation.get("description") or []
        rows.append({"name": name, "repo": repo, "plddt": score,
                     "homolog": annotation.get("homolog", ""),
                     "database": annotation.get("database", ""),
                     "anno": descriptions[0] if descriptions else "",
                     "has_a3m": repo_file(repo, name + ".a3m").is_file()
                     or repo_file(repo, name + ".a3m.gz").is_file()})
    # Build both orders together so changing sort does not repeat ES requests.
    ordered = {}
    created = time.time()
    for order in ("name", "plddt"):
        ordered[order] = sorted(rows, key=(lambda row: (-float(row["plddt"] or -1), row["name"]))
                                if order == "plddt" else lambda row: row["name"])
        path = settings.CACHE_ROOT / (prefix + "v2_" + order + ".json")
        atomic_write(path, json.dumps({"directory_mtime": directory_mtime,
                                     "created": created, "rows": ordered[order]}).encode())
    return ordered[sort]


def clear_browse(repo: str) -> None:
    component(repo)
    prefix = "MP_BROWSE_" + hashlib.sha256(repo.encode()).hexdigest() + "_"
    for path in settings.CACHE_ROOT.glob(prefix + "*.json"):
        path.unlink(missing_ok=True)
