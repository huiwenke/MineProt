# MineProt API Manual

This manual describes the current Python Web service. All paths are relative to
your MineProt base URL. Examples use the local production management service,
`http://127.0.0.1:8081`. Use your public URL for read operations or the writable
Web URL in development. Repository files and Elasticsearch metadata are
managed separately: uploading a structure does not
create its search document, and indexing a protein does not upload its files.

## Contents

1. [Conventions and limits](#1-conventions-and-limits)
2. [Health check](#2-health-check)
3. [Structure conversion](#3-structure-conversion)
4. [Elasticsearch metadata](#4-elasticsearch-metadata)
5. [Repository file access](#5-repository-file-access)
6. [Batch repository imports](#6-batch-repository-imports)
7. [Legacy single-file imports](#7-legacy-single-file-imports)
8. [Structure alignment: Salign](#8-structure-alignment-salign)
9. [Cache management](#9-cache-management)
10. [PAE visualization](#10-pae-visualization)
11. [Errors](#11-errors)

## 1. Conventions and limits

- Use JSON requests with `Content-Type: application/json` unless an endpoint
  specifies form data, multipart data, or a gzip-compressed JSON body.
- GET parameters belong in the query string, not a JSON body.
- Repository names and file names must be single path components. Empty names,
  `.`, `..`, `/`, backslashes and null bytes are rejected. Follow Elasticsearch
  index-naming rules when creating search indexes.
- Base64 values use standard Base64 over UTF-8 text or raw file bytes, as
  specified. Percent-encode Base64 when placing it in a URL; characters such as
  `+`, `/` and `=` must not be interpreted as URL delimiters or form syntax.
- The default maximum request body is **100 MiB** (`104857600` bytes), including
  multipart overhead. Configure it with `MP_MAX_BODY_BYTES`. Import endpoints
  also enforce limits on decoded file content or decompressed JSON as applicable.
- Conversion and single-file import endpoints documented with a trailing slash
  also accept an explicit `index.php` suffix, such as
  `/api/fcz2pdb/index.php`. Batch endpoints use the exact paths shown below.
- In production (`MP_READ_ONLY=true`), public Web returns **403** for all
  repository import paths (including preflight and legacy aliases), ES add/delete,
  `/import.php` and explicit cache clear/update. Use the local management service
  for those operations. Search/get, file access, conversion, PAE and Salign remain
  available. This is a service-level rule, independent of forwarded client IP.
- The application does not implement API authentication. Access control and TLS
  can be provided by a reverse proxy. Keep management bound to loopback; see
  the [production deployment guide](Deployment-manual.md#production-public-read-only-access-and-local-management).

Python examples below use:

```python
import base64
import gzip
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

import requests

BASE = "http://127.0.0.1:8081"
```

## 2. Health check

```http
GET /healthz
```

Returns HTTP `200` with:

```json
{"status": "ok"}
```

This is a Web-process liveness check, not an Elasticsearch or US-align test.

## 3. Structure conversion

Conversion endpoints return structure text and do not save it to a repository.

### 3.1 PDB to AlphaFold-style mmCIF

```http
POST /api/pdb2alphacif/
Content-Type: application/json
```

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `data` | string | Yes | Base64-encoded PDB bytes. |
| `name` | string | No | Structure name; defaults to `model`. |

```python
from pathlib import Path

response = requests.post(
    BASE + "/api/pdb2alphacif/",
    json={
        "name": "protein_001",
        "data": base64.b64encode(Path("protein_001.pdb").read_bytes()).decode(),
    },
    timeout=120,
)
response.raise_for_status()
Path("protein_001.cif").write_bytes(response.content)
```

**Response:** HTTP `200`, `text/plain`, containing mmCIF text. The converter
uses PDB B-factors as pLDDT, adds sequence and ModelCIF quality information for
visualization, and omits hydrogen atoms, including D/T isotopes. Use this
endpoint for predicted structures whose B-factors represent confidence.

### 3.2 mmCIF to PDB

```http
POST /api/cif2pdb/
Content-Type: application/json
```

The JSON body contains `data`, the Base64-encoded mmCIF bytes.

**Response:** HTTP `200`, `text/plain`, containing PDB text.

### 3.3 FCZ to PDB

```http
POST /api/fcz2pdb/
Content-Type: multipart/form-data
```

Upload the FCZ bytes in a file part named **`file`**. This endpoint does not
accept Base64 JSON or a raw binary request body.

```python
with open("protein_001.fcz", "rb") as stream:
    response = requests.post(
        BASE + "/api/fcz2pdb/",
        files={"file": ("protein_001.fcz", stream, "application/octet-stream")},
        timeout=360,
    )
response.raise_for_status()
pdb_bytes = response.content
```

**Response:** HTTP `200`, `text/plain`, containing PDB text. Invalid FCZ inputs
return `400`; decoding timeouts return `502`. Decoding runs in an isolated
Python process, with a default timeout of 300 seconds controlled by
`MP_FOLDCOMP_TIMEOUT`.

## 4. Elasticsearch metadata

These endpoints operate on Elasticsearch documents, not repository files.
Use one Elasticsearch index per repository and the same protein name in both.

### 4.1 Document schema and IDs

A typical protein document is:

```json
{
  "name": "protein_001",
  "seq": "MAVK",
  "score": 92.5,
  "anno": {
    "homolog": "P12345",
    "database": "uniprotkb",
    "description": ["Example protein annotation", "protein_001"]
  }
}
```

| Field | Meaning |
| --- | --- |
| `name` | Protein file stem, without `.pdb`, `.cif` or `.fcz`. |
| `seq` | One-letter amino-acid sequence. |
| `score` | Mean confidence/pLDDT, or `-1.0` when unavailable. |
| `anno.homolog` | Homolog identifier; use an empty string when unavailable. |
| `anno.database` | Database name, such as `uniprotkb` or `afdb`; empty when unavailable. |
| `anno.description` | Searchable strings. The first entry is the displayed annotation; a second entry can contain the protein name. |

The proxy forwards valid JSON without enforcing this schema. Clients should
provide these fields consistently. Search cards display the first description
as a link. With no homolog, it links to a Bing search for that description;
otherwise the existing database-specific homolog link is used.

MineProt's toolkit and browse lookup use **Base64 of the UTF-8 protein name**
as the Elasticsearch document ID. Follow the same convention:

```python
name = "protein_001"
document_id = base64.b64encode(name.encode("utf-8")).decode("ascii")
encoded_id = quote(document_id, safe="")
```

### 4.2 Add or replace a protein document

```http
POST /api/es/{repo}/add/{document_id}
Content-Type: application/json
```

The body is the complete protein document. An existing document with the same
ID is replaced; this is not a partial update.

**Response:** HTTP `200` with an **empty body** on success. Do not call
`response.json()` on a successful add response. This endpoint does not return
the Elasticsearch Index API JSON response. Elasticsearch client-error statuses
are propagated, while backend availability failures generally return `502`.

```python
response = requests.post(
    f"{BASE}/api/es/demo/add/{encoded_id}",
    json={
        "name": name,
        "seq": "MAVK",
        "score": -1.0,
        "anno": {
            "homolog": "",
            "database": "",
            "description": ["Example annotation", name],
        },
    },
    timeout=60,
)
response.raise_for_status()
```

### 4.3 Get a protein document

```http
GET /api/es/{repo}/get/{document_id}
```

`POST` is also accepted. The response contains the Elasticsearch Get API JSON,
including `found` and `_source` when present. A missing document or index may
return HTTP `404`; inspect the response status before parsing the result.

### 4.4 Delete a document or an index

| Operation | URL |
| --- | --- |
| Delete one document | `/api/es/{repo}/del/{document_id}` |
| Delete the entire metadata index | `/api/es/{repo}/del/` |

Use `POST` or `DELETE`. The response contains the corresponding Elasticsearch
JSON and status. Deleting an index removes all its metadata documents but does
not delete the repository's structure files.

### 4.5 Search annotations

```http
GET /api/es/{repo}/search/{term}
```

`POST` is also accepted. `{term}` is the percent-encoded Base64 representation
of the UTF-8 search text. A comma-separated repository list is supported.

```python
term = quote(base64.b64encode("ATP synthase".encode()).decode(), safe="")
response = requests.get(f"{BASE}/api/es/demo/search/{term}", timeout=60)
response.raise_for_status()
hits = response.json()
```

**Response:** HTTP `200`, `application/json`, containing the **hits array**,
not the full Elasticsearch search response:

```json
[
  {
    "_index": "demo",
    "_id": "cHJvdGVpbl8wMDE=",
    "_score": 1.0,
    "_source": {
      "name": "protein_001",
      "seq": "MAVK",
      "score": 92.5,
      "anno": {
        "homolog": "",
        "database": "",
        "description": ["ATP synthase", "protein_001"]
      }
    }
  }
]
```

Search uses `match_phrase` on `anno.description`, returns at most **200 hits**,
and exposes no pagination parameters. No matches or a missing index produce
an empty array.

## 5. Repository file access

### 5.1 Converted or decompressed file content

```http
GET /api/file/{repo}/{name}
HEAD /api/file/{repo}/{name}
```

Include the desired extension in `{name}`. For example:

```text
/api/file/demo/protein_001.pdb
/api/file/demo/protein_001.cif?viewer=modern
/api/file/demo/protein_001.json
```

- A `.pdb` request can use the matching PDB, gzipped PDB, FCZ or CIF structure.
- A `.cif` request can use a stored CIF or convert a matching PDB/FCZ structure.
- A request for an ordinary file can fall back to its `.gz` variant.
- Direct `.fcz` requests decode FCZ to PDB content. Use a `.pdb` request when
  you also want the response content type to be `text/plain`.
- A stored CIF requested without `viewer=modern` receives legacy-viewer
  adaptations, including hydrogen removal. `viewer=modern` bypasses those
  additional adaptations; conversion may still occur if no CIF is stored.

Missing files return `404`. For the original stored bytes, use `/repo/` instead.

### 5.2 Raw files and directory listings

```http
GET /repo/{repo}/{name}
HEAD /repo/{repo}/{name}
```

Files are served as stored: `.fcz` remains FCZ and `.gz` remains gzip. No
structure conversion is performed. `/repo/` and repository directory URLs
return HTML directory listings.

## 6. Batch repository imports

Use batch imports for large repositories. The protocol separates preflight
checks from binary uploads and avoids Base64 expansion.

### 6.1 Manifest

Both batch endpoints use the same manifest structure. This valid example
represents a two-byte JSON file containing `{}`:

```json
{
  "repo": "demo",
  "force": false,
  "files": [
    {
      "name": "protein_001.json",
      "storage": "gzip",
      "encoding": "gzip",
      "size": 2,
      "sha256": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
    }
  ]
}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `repo` | Yes | Target repository name. |
| `force` | No | Boolean; defaults to `false`. Allow different content to replace a file in the same storage format. |
| `files` | Yes | Array of 1–256 entries. Duplicate logical files, including a same-stem PDB and FCZ pair, are rejected. |
| `files[].name` | Yes | Logical file name. Use `.pdb`, `.cif`, `.json`, `.a3m` or `.fcz`, without a `.gz` suffix. |
| `files[].storage` | Yes | `plain`, `gzip` or `fcz`. Only `.fcz` files use `fcz`; FCZ cannot use `plain` or `gzip`. |
| `files[].encoding` | No | Transport encoding: `identity` (default) or `gzip`. FCZ requires `identity`. |
| `files[].size` | Yes | Number of bytes after removing transport gzip, if present. |
| `files[].sha256` | Yes | Lowercase, 64-character SHA-256 of those same bytes. |
| `files[].content_sha256` | For FCZ only | SHA-256 of the UTF-8 PDB text returned by `foldcomp.decompress(fcz_bytes)[1]`. |

**Transport compression and storage compression are independent.** A gzip
transport can be stored as plain content, and an uncompressed transport can be
stored as gzip. For ordinary files, `size` and `sha256` always describe the
uncompressed content. For FCZ, they describe the FCZ bytes themselves.

FCZ files can have different bytes after repeated compression of the same
structure. The byte hash verifies uploaded data; `content_sha256` compares the
PDB decoded from each FCZ. It does not compare a lossy FCZ reconstruction with
the original PDB.

### 6.2 Storage-format rules

| Requested storage | Expected server file |
| --- | --- |
| `plain` | The exact logical file name, such as `protein_001.pdb`. |
| `gzip` | The logical file name plus `.gz`, such as `protein_001.pdb.gz`. |
| `fcz` | The exact `.fcz` file name. |

For a PDB/FCZ structure, the server checks all matching `.pdb`, `.pdb.gz`,
`.fcz` and `.fcz.gz` variants before deciding whether an import is allowed.

- If the existing storage format differs, the file is reported as an error.
- `force=true` does not bypass a storage-format conflict.
- Existing same-format, identical content is skipped, even with `force=true`.
- Existing same-format, different content is skipped unless `force=true`.
- Multiple variants for one structure are reported as a conflict.
- New `.fcz.gz` imports are prohibited; existing `.fcz.gz` files are reported
  as unsupported by the import protocol. This does not remove legacy files.

### 6.3 Batch preflight

```http
POST /api/import2repo/batch/check
Content-Type: application/json
```

Send the manifest as the JSON body. The server does not write protein files.
It returns a result for each entry and its current request limits:

```json
{
  "results": [{"name": "protein_001.json", "status": "upload"}],
  "max_files": 256,
  "max_body_bytes": 104857600
}
```

| Status | Meaning |
| --- | --- |
| `upload` | Missing file, or same-format different content with `force=true`. |
| `unchanged` | Same-format content already matches. |
| `exists` | Same-format content differs and `force=false`; no replacement allowed. |
| `error` | Conflict, invalid existing content, file-size limit or another per-file failure. The entry includes `error` text. |

Preflight is not a reservation. The upload endpoint rechecks repository state
before committing each file.

### 6.4 Batch upload

```http
POST /api/import2repo/batch
Content-Type: multipart/form-data
```

Send exactly:

- One text field named **`manifest`**, containing the JSON manifest.
- One file part for each manifest entry, named **`file0`**, **`file1`**, and so
  on, in manifest order. Part names restart at `file0` for each request.

Do not send the manifest as a file part. Do not include skipped entries in the
upload manifest. Extra, missing or duplicate form parts are rejected.

A complete ordinary-file example:

```python
import gzip
import hashlib
import json

content = b"{}"
entry = {
    "name": "protein_001.json",
    "storage": "gzip",
    "encoding": "gzip",
    "size": len(content),
    "sha256": hashlib.sha256(content).hexdigest(),
}
manifest = {"repo": "demo", "force": False, "files": [entry]}

with requests.Session() as session:
    response = session.post(
        BASE + "/api/import2repo/batch/check", json=manifest, timeout=360
    )
    response.raise_for_status()
    preflight = response.json()
    if preflight["results"][0]["status"] == "upload":
        response = session.post(
            BASE + "/api/import2repo/batch",
            data={"manifest": json.dumps(manifest)},
            files={
                "file0": (
                    entry["name"], gzip.compress(content, mtime=0),
                    "application/octet-stream",
                )
            },
            timeout=600,
        )
        response.raise_for_status()
        print(response.json())  # Inspect every file result, even on HTTP 200.
    else:
        print(preflight["results"])
```

For FCZ, prepare the entry and payload as follows, then use the same preflight
and upload flow with the FCZ bytes as `file0`:

```python
from pathlib import Path
import foldcomp  # pip install foldcomp==1.0.0

source = Path("protein_001.pdb")
fcz_bytes = foldcomp.compress(source.stem, source.read_text(encoding="utf-8"))
decoded_pdb = foldcomp.decompress(fcz_bytes)[1].encode("utf-8")
entry = {
    "name": source.with_suffix(".fcz").name,
    "storage": "fcz",
    "encoding": "identity",
    "size": len(fcz_bytes),
    "sha256": hashlib.sha256(fcz_bytes).hexdigest(),
    "content_sha256": hashlib.sha256(decoded_pdb).hexdigest(),
}
```

The Foldcomp compression interface used by the toolkit requires a single-chain
PDB. Unsupported structures fail explicitly rather than silently changing
format. FCZ is lossy; retain the source PDB when exact preservation is required.

**Response:** HTTP `200` with a `results` array. Successful writes use
`status: "imported"`; skipped files use `unchanged` or `exists`; failed files
use `error` and an explanatory message:

```json
{
  "results": [
    {"name": "protein_001.fcz", "status": "imported"},
    {"name": "protein_002.fcz", "status": "error", "error": "Invalid FCZ file"}
  ]
}
```

Files are committed atomically and independently. One failure does not roll
back other files. Browse caches are invalidated once per changed batch.
Requests may be retried: completed matching files are recognized as unchanged.
FCZ validation reuses an isolated worker per batch and replaces it after a
native crash or timeout.

### 6.5 Toolkit client

```bash
# Local PDBs -> server-side gzip PDBs.
python toolkit/scripts/batch/import_repo.py -i /path/to/pdb -n demo -m 3 -z

# Local PDBs -> FCZ files.
python toolkit/scripts/batch/import_repo.py -i /path/to/pdb -n demo -m 4
```

The client defaults to 256 files per batch, a target of approximately 16 MiB
per batch, and two concurrent batches. Adjust `--batch-files`, `--batch-mib`
and `--workers`; use `--url` for another server. The client requires a server
with batch import support and does not silently fall back to single uploads.
`-z` selects gzip storage and is incompatible with `-m 4`.

## 7. Legacy single-file imports

These endpoints remain available for older clients. Prefer batch imports for
new integrations.

### 7.1 Check an existing file

```http
GET /api/import2repo/check.php?repo=demo&name=protein_001.pdb&gzip=true
```

| Query parameter | Required | Meaning |
| --- | --- | --- |
| `repo` | Yes | Target repository. |
| `name` | Yes | Logical file name, including extension but excluding `.gz`. |
| `gzip` | No | Boolean; defaults to `false`. Require gzip storage when `true`. |

**Response:** HTTP `200`, `text/plain`, containing the lowercase MD5 digest,
or an empty body if the file is absent. Gzip files are decompressed before
hashing, so an uncompressed local file can be compared with its server gzip
variant. For `.fcz`, the legacy endpoint hashes raw FCZ bytes; use batch
preflight for decoded-content comparison. Storage-format conflicts return `400`.

### 7.2 Import one file

```http
POST /api/import2repo/
```

The request body must be **gzip-compressed JSON**, not plain JSON. Its decoded
form is:

```json
{
  "repo": "demo",
  "name": "protein_001.pdb",
  "text": "BASE64_ENCODED_FILE_BYTES",
  "force": false,
  "gzip": true
}
```

`name` includes the extension. `text` holds Base64-encoded original file bytes,
not gzip bytes. `force` and `gzip` default to `false`. The latter selects
storage compression; it is independent of the always-gzipped JSON request.
FCZ may be supplied as `.fcz` with `gzip=false`, but `.fcz.gz` is prohibited.
The server validates FCZ and derives its decoded-content hash internally.

```python
from pathlib import Path

body = {
    "repo": "demo",
    "name": "protein_001.pdb",
    "text": base64.b64encode(Path("protein_001.pdb").read_bytes()).decode(),
    "force": False,
    "gzip": True,
}
response = requests.post(
    BASE + "/api/import2repo/",
    data=gzip.compress(json.dumps(body).encode("utf-8")),
    headers={"Content-Type": "application/json"},
    timeout=600,
)
response.raise_for_status()
print(response.text)
```

Send the compressed bytes yourself. The current handler expects them directly;
a `Content-Encoding` header alone does not perform compression.

**Response:** HTTP `200`, `text/plain`, containing `Importing` or `Skipping`.
Per-file commit errors, including storage conflicts, return `409` with plain
text. Request validation or initial FCZ decoding failures can return `400` or
`502`. Storage rules are the same as for batch imports: `force` cannot switch
between plain, gzip and FCZ formats.

## 8. Structure alignment: Salign

### 8.1 Submit an alignment job

```http
POST /api/salign/
Content-Type: application/x-www-form-urlencoded
```

Multipart form data is also accepted. This endpoint expects **form fields**,
not a JSON body.

| Field | Required | Meaning |
| --- | --- | --- |
| `structure` | Yes | Query PDB or mmCIF text, not Base64 and not a file-part upload. |
| `repo[]` | No | Repository to search. Repeat the field for multiple repositories; omission selects available repositories. |
| `search` | No | Annotation phrase restricting targets; defaults to empty. |
| `hinge` | No | Integer from 0 to 9; defaults to 0. Used only for single-chain pairs; ignored in complex mode. |
| `tmscore` | No | TM-score display threshold from 0 to 1; defaults to 0.5. |

Without `search`, targets are the structure names in the selected repository
directories. With `search`, targets are the annotation search hits, subject to
the 200-hit search limit. The former `rmsd` parameter is not used by the current
submission handler.

For each query/target pair, the backend counts polymer chains in the first model.
If either structure contains more than one polymer chain, it runs US-align with
`-mm 1 -fast`. Otherwise it uses `-mm 7 -afp -hinge N -fast`. Water and
non-polymer ligands do not trigger complex mode, and extra models are not
counted as extra chains. The Detail endpoint uses the same rule.

The browser can read a local PDB/CIF file and submit its contents as `structure`;
this does not add a multipart file-upload API. The browser file limit is the
smaller of 20 MiB and one quarter of `MP_MAX_BODY_BYTES`, leaving room for form
encoding. Direct API requests remain subject to the overall request-body limit.

```python
response = requests.post(
    BASE + "/api/salign/",
    data={
        "repo[]": ["demo"],
        "structure": Path("query.pdb").read_text(),
        "hinge": 0,
        "tmscore": 0.5,
    },
    allow_redirects=False,
    timeout=120,
)
if response.status_code != 302:
    response.raise_for_status()
    raise RuntimeError("Expected a Salign result redirect")
result_url = response.headers["Location"]
```

**Response:** HTTP `302` with a `Location` header such as:

```text
/salign/result.php?rid=<job-id>&tmscore=0.5
```

The endpoint does **not** return a plain-text job ID. Disable automatic redirect
following if you need to capture the job URL directly.

### 8.2 View results and download files

```http
GET /salign/result.php?rid={job-id}&tmscore=0.5
```

This returns an HTML results page, not a JSON job-status object. States include
`queued`, `running`, `packaging`, `complete` and `failed`. Active jobs generally
return `Refresh: 5` while results are pending. The page includes links to
alignment files and the completed `result.tar.gz` archive. The PDBe Mol* 3.12.0
viewer initially shows the aligned query in gray and the target with its default
pLDDT display; both structures remain visible.

The results page filters hits using the larger of the two reported TM-scores
and sorts retained hits by their mean TM-score. `tmscore` changes the displayed
results rather than the target set submitted to US-align.

Use the cache download URLs generated by the results page. For the archive,
the decoded cache path is `MP_SALIGN_{job-id}/result.tar.gz`.

```http
GET /salign/detail.php?pdb1={base64-cache-path}&pdb2={base64-cache-path}
```

This returns an HTML US-align detail report using paths generated by the
results page. Query parameters must be percent-encoded.

`MP_SALIGN_CONCURRENCY` defaults to 2 simultaneous jobs;
`MP_SALIGN_TIMEOUT` defaults to 300 seconds per US-align invocation. Queued jobs
wait for a slot. A job whose worker is lost can be marked failed when its result
page is opened; submit a new job to retry it.

## 9. Cache management

### 9.1 Download a cache file

```http
GET /api/cache/get.php?data_url={base64-path}
```

`data_url` is the percent-encoded Base64 representation of a cache-relative
path, or an absolute path inside the configured cache root. For example,
encode `MP_SALIGN_{job-id}/result.tar.gz` to download an alignment archive.
Paths outside the cache root are rejected.

The response contains the stored bytes. A nonempty `download` query parameter
adds attachment headers and uses `application/octet-stream`; otherwise the
response content type is inferred from the file.

### 9.2 Invalidate a repository's browse cache

```http
GET /api/cache/clear.php?repo=demo
```

Returns HTTP `200` with an empty body. The next browse request rebuilds the
cache as needed. This operation does not delete repository files, metadata
indexes or Salign jobs. The legacy `force` parameter is accepted but unused.

### 9.3 Rebuild browse caches and clean up old jobs

```http
GET /api/cache/update.php
POST /api/cache/update.php
```

Rebuilds both name-sorted and pLDDT-sorted browse caches for available
repositories. Also removes completed or failed Salign job directories whose
status-file modification time is more than 24 hours old; active jobs are not
removed. This does not clear all alignment results indiscriminately.

**Response:** HTTP `200` with an empty body when finished. This is synchronous
and may require a long client timeout for large repositories. The old
Linux-only note is not an API-specific restriction; the endpoint runs wherever
the current server deployment is supported.

## 10. PAE visualization

```http
GET /api/plot/pae.php?data_url={base64-repository-json-url}
```

Encode a path such as `/api/file/demo/protein_001.json` using UTF-8 Base64, then
percent-encode the value for the query string. A full URL with the same path
shape is also accepted, but its host is not fetched: the JSON is resolved from
the local repository.

The source JSON must contain a nonempty square `pae` matrix of finite,
nonnegative numbers. Optional `max_pae` must be finite and positive and defaults
to **31.75** when absent:

```json
{
  "pae": [[0.0, 1.2], [1.1, 0.0]],
  "max_pae": 31.75
}
```

**Response:** HTTP `200`, `text/html`, containing an interactive PAE heatmap,
chain/token strip and PDBe Mol* 3.12.0 structure viewer. The matrix is directional:
rows are aligned/reference tokens; columns are scored tokens. Hover inspects a
pair, click pins it, dragging a box selects two ranges, and dragging along the
sequence strip selects a range. The page also provides clear/reset controls,
PAE image export and a JSON download.

For AlphaFold3, preserve `token_chain_ids` and `token_res_ids` alongside `pae`.
These arrays must match the matrix length and describe the chain and residue ID
of each token. `atom_chain_ids` and `atom_plddts` can help verify atom order for
repeated residue tokens, such as ligands. Mapping uses the matching CIF and
selects only unambiguous positions; affected unmapped tokens have linking
unavailable while the PAE matrix remains usable. Without token metadata, the
server attempts sequence-based mapping. If the structure cannot be read,
PAE still displays with a warning and structure linking disabled.

The page requests its structure through `/api/file/{repo}/{name}.cif?viewer=modern`.
It resolves JSON locally and never fetches an arbitrary external `data_url` host.

## 11. Errors

Most application errors return plain text, while framework validation errors
may return JSON. Elasticsearch get/delete responses retain upstream JSON and
client-error statuses. Do not assume all error bodies are JSON.

| HTTP status | Typical meaning |
| --- | --- |
| `400` | Invalid value, Base64, gzip, structure input, manifest, multipart form or missing JSON field. |
| `403` | Management operation requested through a read-only public service. |
| `404` | Missing file, unknown operation, job directory or Elasticsearch document/index. |
| `409` | Legacy single-file import commit error, including a storage-format conflict. |
| `413` | Request body exceeds the configured maximum size. |
| `422` | Framework-level validation failure, such as a missing required query parameter. |
| `502` | Backend failure, unavailable Elasticsearch, decoding timeout or failed external-tool invocation. |

For batch imports, HTTP `200` means the batch was processed, **not that every
file succeeded**. Always inspect every entry in `results`. Per-file failures
remain in that array; malformed whole requests can fail before any file is
committed. Successful files are not rolled back when another entry fails.
