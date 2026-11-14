"""Import repository files using bounded, retryable binary batches."""

import gzip
import hashlib
import json
import threading

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_LOCAL = threading.local()


def session():
    if not hasattr(_LOCAL, "session"):
        client = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            allowed_methods=frozenset(["POST"]),
            status_forcelist=[429, 502, 503, 504],
        )
        client.mount("http://", HTTPAdapter(max_retries=retry))
        client.mount("https://", HTTPAdapter(max_retries=retry))
        _LOCAL.session = client
    return _LOCAL.session


def request(url, **kwargs):
    response = session().post(url, timeout=(10, 600), **kwargs)
    if response.status_code == 404:
        raise RuntimeError(
            "Server does not support batch imports; upgrade the MineProt Web service"
        )
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict) or not isinstance(result.get("results"), list):
        raise RuntimeError("Invalid batch response from server")
    return result


def results_by_name(result, names):
    entries = result["results"]
    if len(entries) != len(names) or {item["name"] for item in entries} != set(names):
        raise RuntimeError("Server returned an incomplete batch result")
    return {item["name"]: item for item in entries}


def prepare(path, mode, compressed):
    data = path.read_bytes()
    name = path.name
    storage = "gzip" if compressed else "plain"
    if mode == 4:
        import foldcomp

        data = foldcomp.compress(path.stem, data.decode("utf-8"))
        name = path.with_suffix(".fcz").name
        storage = "fcz"
    item = {
        "name": name,
        "storage": storage,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "encoding": "identity" if mode == 4 else "gzip",
    }
    if mode == 4:
        item["content_sha256"] = hashlib.sha256(
            foldcomp.decompress(data)[1].encode("utf-8")
        ).hexdigest()
    payload = data if mode == 4 else gzip.compress(data, mtime=0)
    return item, payload


def upload_batch(args, batch):
    body = {"repo": args.n, "force": args.f, "files": [item for item, _ in batch]}
    checked = request(args.url.rstrip("/") + "/batch/check", json=body)
    statuses = results_by_name(checked, [item["name"] for item, _ in batch])
    results = []
    pending = []
    for item, payload in batch:
        result = statuses[item["name"]]
        if result["status"] == "upload":
            pending.append((item, payload))
        elif result["status"] in ("unchanged", "exists", "error"):
            results.append(result)
        else:
            raise RuntimeError("Unexpected preflight status: " + str(result["status"]))
    if not pending:
        return results
    server_limit = checked["max_body_bytes"]
    # Split further if the server advertises a smaller request limit.
    groups = []
    group, size = [], 4096
    for item, payload in pending:
        cost = len(payload) + len(json.dumps(item).encode()) + 1024
        if cost + 4096 > server_limit:
            results.append(
                {
                    "name": item["name"],
                    "status": "error",
                    "error": "File exceeds server upload limit",
                }
            )
            continue
        if group and size + cost > server_limit:
            groups.append(group)
            group, size = [], 4096
        group.append((item, payload))
        size += cost
    if group:
        groups.append(group)
    for group in groups:
        body["files"] = [item for item, _ in group]
        files = [
            ("file" + str(i), (item["name"], payload, "application/octet-stream"))
            for i, (item, payload) in enumerate(group)
        ]
        response = request(
            args.url.rstrip("/") + "/batch", data={"manifest": json.dumps(body)}, files=files
        )
        received = results_by_name(response, [item["name"] for item, _ in group])
        results.extend(received.values())
    return results
