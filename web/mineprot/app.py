"""HTTP compatibility layer for the original MineProt frontend and toolkit.

Run from web/: uvicorn mineprot.app:app --host 0.0.0.0 --port 8000
"""
import base64
from contextlib import asynccontextmanager
import gzip
import hashlib
import html
import io
import json
import logging
import math
import mimetypes
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import quote, urlencode, urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool
from starlette.middleware.gzip import GZipMiddleware

from . import imports, jobs, pae, search, settings
from .storage import (atomic_write, b64decode, bounded_gunzip, component, decompress_fcz,
                      inside, protein_names, read_file, repo_file)
from .structures import cif_to_pdb, pdb_to_alphacif, viewer_cif

logger = logging.getLogger("mineprot")


class BodyLimitMiddleware:
    """Bound both declared and streamed bodies before handlers can write files."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            return await PlainTextResponse("Invalid Content-Length", status_code=400)(scope, receive, send)
        if length > settings.MAX_BODY:
            return await PlainTextResponse("Request too large", status_code=413)(scope, receive, send)
        # Keep bounded memory even when multiple batches arrive concurrently.
        with tempfile.SpooledTemporaryFile(max_size=1024 * 1024) as body:
            size = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > settings.MAX_BODY:
                    return await PlainTextResponse("Request too large", status_code=413)(scope, receive, send)
                body.write(chunk)
                if not message.get("more_body", False):
                    break
            body.seek(0)
            remaining = size

            async def replay():
                nonlocal remaining
                if remaining is None:
                    return await receive()
                chunk = body.read(65536)
                remaining -= len(chunk)
                more = remaining > 0
                if not more:
                    remaining = None
                return {"type": "http.request", "body": chunk, "more_body": more}
            await self.app(scope, replay, send)


@asynccontextmanager
async def lifespan(app):
    settings.REPO_ROOT.mkdir(parents=True, exist_ok=True)
    settings.CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="MineProt", lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)
app.add_middleware(BodyLimitMiddleware)
app.mount("/assets", StaticFiles(directory=settings.WEB_ROOT / "assets"), name="assets")
templates = Jinja2Templates(directory=settings.WEB_ROOT / "templates")
templates.env.filters["b64"] = lambda value: base64.b64encode(str(value).encode()).decode()


def token(value: str) -> str:
    return quote(base64.b64encode(value.encode()).decode(), safe="")


def homolog_url(annotation):
    homolog = quote(annotation.get("homolog", ""), safe="")
    if annotation.get("database") == "afdb":
        return "https://alphafold.com/entry/" + homolog
    return "https://www.uniprot.org/" + quote(annotation.get("database", ""), safe="") + "?query=" + homolog


def mime(name):
    return {".json": "application/json", ".pdb": "text/plain", ".cif": "text/plain",
            ".a3m": "text/plain"}.get(Path(name).suffix, "application/octet-stream")


@app.exception_handler(FileNotFoundError)
async def missing(request, exc):
    return PlainTextResponse("File not found", status_code=404)


@app.exception_handler(gzip.BadGzipFile)
@app.exception_handler(UnicodeError)
@app.exception_handler(ValueError)
async def invalid(request, exc):
    return PlainTextResponse(str(exc), status_code=400)


@app.exception_handler(KeyError)
async def missing_field(request, exc):
    return PlainTextResponse("Missing field: " + str(exc), status_code=400)


@app.exception_handler(httpx.HTTPError)
@app.exception_handler(subprocess.SubprocessError)
@app.exception_handler(RuntimeError)
async def upstream_error(request, exc):
    logger.exception("Backend operation failed", exc_info=exc)
    return PlainTextResponse("Backend operation failed; see server log", status_code=502)


@app.get("/healthz")
def health():
    return {"status": "ok"}


async def context(request):
    repos = await run_in_threadpool(search.datasets)
    selected = request.query_params.getlist("repo[]")
    if not selected and request.query_params.get("repo"):
        selected = [request.query_params["repo"]]
    if "search" in request.query_params and not selected:
        selected = repos
    return {"DATA_REPOS": repos, "selected_repos": selected}


def render(request, name, values, headers=None):
    return templates.TemplateResponse(request=request, name=name, context=values, headers=headers)


@app.api_route("/", methods=["GET", "POST"])
@app.api_route("/index.php", methods=["GET", "POST"])
@app.get("/index.html")
async def home(request: Request):
    return render(request, "index.html", await context(request))


@app.get("/import.php")
async def import_page(request: Request):
    return render(request, "import.html", await context(request))


def paginate(items, form):
    try:
        page = max(1, int(form.get("page", "1")))
    except (TypeError, ValueError):
        page = 1
    total = (len(items) + 9) // 10
    page = min(page, max(1, total))
    return items[(page - 1) * 10:page * 10], {"page": page, "top": (page - 1) * 10, "tot": total, "length": 10}


def decorate_search(hit):
    source = hit.get("_source", {})
    source.setdefault("anno", {})
    annotation = source["anno"] or {}
    descriptions = annotation.get("description") or []
    description = (descriptions[0] or "") if descriptions else ""
    annotation_url = (homolog_url(annotation) if annotation.get("homolog") else
                      "https://www.bing.com/search?" + urlencode({"q": description}))
    path = "/api/file/" + quote(hit["_index"], safe="") + "/" + quote(source["name"], safe="")
    hit["_view"] = {
        "annotation": annotation, "annotation_description": description, "homolog_url": annotation_url,
        "b64_Data_URL": token(path + ".json"),
        "Search_Result_Viewer": "MP_" + hashlib.md5((hit["_index"] + "/" + source["name"]).encode()).hexdigest(),
        "Search_Result_Path": path + ".cif?viewer=modern"}
    return hit


@app.api_route("/search.php", methods=["GET", "POST"])
async def search_page(request: Request):
    values = await context(request)
    term = request.query_params.get("search", "")
    repos = values["selected_repos"] or values["DATA_REPOS"]
    hits = await run_in_threadpool(search.search, repos, term)
    raw = json.dumps(hits, ensure_ascii=False)
    for index, hit in enumerate(hits):
        if hit.get("_source", {}).get("name") == term:
            hits[0], hits[index] = hits[index], hits[0]
            break
    displayed, info = paginate(hits, await request.form(max_part_size=settings.MAX_BODY) if request.method == "POST" else {})
    values.update(search_term=term, search_json=raw, Search_Result_Num=len(hits),
                  displayed=[decorate_search(hit) for hit in displayed], Page_Info=info)
    return render(request, "search.html", values)


@app.api_route("/browse.php", methods=["GET", "POST"])
async def browse_page(request: Request):
    values = await context(request)
    repo = request.query_params.get("repo", "")
    form = await request.form(max_part_size=settings.MAX_BODY) if request.method == "POST" else {}
    sort = "plddt" if form.get("sort", request.query_params.get("sort")) == "plddt" else "name"
    rows = await run_in_threadpool(search.browse_cache, repo, sort) if repo else []
    total = len(rows)
    page_size = 1000
    pages = max(1, (total + page_size - 1) // page_size)
    try:
        page = min(pages, max(1, int(request.query_params.get("page", "1"))))
    except ValueError:
        page = 1
    rows = rows[(page - 1) * page_size:page * page_size]
    for row in rows:
        row["homolog_url"] = (homolog_url(row) if row.get("homolog") else
                              "https://www.bing.com/search?" + urlencode({"q": row["anno"]}))
    values.update(repo=repo, rows=rows, sort=sort, total=total, page=page, pages=pages, page_size=page_size,
                  first_url="/browse.php?" + urlencode({"repo": repo, "sort": sort, "page": 1}),
                  last_url="/browse.php?" + urlencode({"repo": repo, "sort": sort, "page": pages}),
                  previous_url="/browse.php?" + urlencode({"repo": repo, "sort": sort, "page": page - 1}),
                  next_url="/browse.php?" + urlencode({"repo": repo, "sort": sort, "page": page + 1}))
    return render(request, "browse.html", values)


# Do not redirect trailing-slash legacy POST requests: serve directory and
# index.php aliases explicitly, including the empty document ID for index ops.
@app.api_route("/api/es/{repo}/{action}", methods=["GET", "POST", "DELETE"])
@app.api_route("/api/es/{repo}/{action}/{term:path}", methods=["GET", "POST", "DELETE"])
async def es_api(request: Request, repo: str, action: str, term: str = ""):
    if action not in ("get", "add", "del", "search"):
        raise HTTPException(404, "Unknown operation")
    if action == "search":
        result = await run_in_threadpool(search.search, repo.split(","), b64decode(term).decode())
        return Response(json.dumps(result), media_type="application/json")
    indexes = ",".join(quote(component(value), safe="*") for value in repo.split(","))
    path = indexes + ("/_doc/" + quote(term, safe="") if term else "")
    if action == "add":
        if not term:
            raise ValueError("Document ID required")
        body = await request.body()
        json.loads(body)
        response = await run_in_threadpool(search.es_request, "POST", path, content=body,
                                          headers={"Content-Type": "application/json"})
        await run_in_threadpool(search.clear_browse, repo)
        # The original add endpoint returns an empty successful body.
        return Response(status_code=response.status_code if response.is_error else 200)
    response = await run_in_threadpool(search.es_request, "DELETE" if action == "del" else "GET", path)
    if action == "del":
        for name in repo.split(","):
            if "*" not in name:
                await run_in_threadpool(search.clear_browse, name)
    return Response(response.content, media_type="application/json", status_code=response.status_code)


@app.api_route("/api/file/{repo}/{name}", methods=["GET", "HEAD"])
def file_api(repo: str, name: str, viewer: str = ""):
    data = read_file(repo, name)
    # Search uses current Molstar; keep the legacy adapter for existing clients.
    if name.lower().endswith(".cif") and viewer != "modern":
        data = viewer_cif(data)
    return Response(data, media_type=mime(name))


@app.post("/api/pdb2alphacif/")
@app.post("/api/pdb2alphacif/index.php")
async def convert_pdb(request: Request):
    body = await request.json()
    name = component(str(body.get("name", "model")))
    data = b64decode(body["data"])
    result = await run_in_threadpool(pdb_to_alphacif, data, name)
    return PlainTextResponse(result)


@app.post("/api/cif2pdb/")
@app.post("/api/cif2pdb/index.php")
async def convert_cif(request: Request):
    body = await request.json()
    result = await run_in_threadpool(cif_to_pdb, b64decode(body["data"]))
    return PlainTextResponse(result)


@app.post("/api/fcz2pdb/")
@app.post("/api/fcz2pdb/index.php")
async def convert_fcz(request: Request):
    async with request.form(max_part_size=settings.MAX_BODY) as form:
        upload = form.get("file")
        if not upload or not hasattr(upload, "read"):
            raise ValueError("Multipart field 'file' required")
        data = await upload.read()
    return Response(await run_in_threadpool(decompress_fcz, data), media_type="text/plain")


@app.post("/api/import2repo/")
@app.post("/api/import2repo/index.php")
async def import_repo(request: Request):
    body = json.loads(bounded_gunzip(await request.body()))
    repo, name = component(body["repo"]), component(body["name"])
    data = b64decode(body["text"])
    if name.endswith('.fcz') and body.get('gzip', False):
        raise ValueError('FCZ + gzip storage is not supported')
    item = {'name': name, 'storage': 'fcz' if name.endswith('.fcz') else ('gzip' if body.get('gzip', False) else 'plain'),
            'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    if item['storage'] == 'fcz':
        decoded = await run_in_threadpool(decompress_fcz, data)
        item['content_sha256'] = hashlib.sha256(decoded).hexdigest()
    result = await run_in_threadpool(imports.commit, {'repo': repo, 'force': body.get('force', False), 'files': [item]}, [io.BytesIO(data)])
    result = result['results'][0]
    if result['status'] == 'error':
        return PlainTextResponse(result['error'], status_code=409)
    return PlainTextResponse('Importing' if result['status'] == 'imported' else 'Skipping')


@app.post('/api/import2repo/batch/check')
async def check_import_batch(request: Request):
    body = imports.manifest(await request.json())
    return await run_in_threadpool(imports.check, body)


@app.post('/api/import2repo/batch')
async def import_batch(request: Request):
    async with request.form(max_files=imports.MAX_FILES, max_fields=1,
                            max_part_size=1024 * 1024) as form:
        body = imports.manifest(json.loads(form['manifest']))
        expected = {'manifest'} | {'file' + str(i) for i in range(len(body['files']))}
        if set(form) != expected or len(form.multi_items()) != len(expected):
            raise ValueError('Multipart files do not match manifest')
        uploads = [form['file' + str(i)] for i in range(len(body['files']))]
        if any(not hasattr(upload, 'file') for upload in uploads):
            raise ValueError('Missing multipart file')
        return await run_in_threadpool(imports.commit, body, [upload.file for upload in uploads])


@app.get("/api/import2repo/check.php")
def check_import(repo: str, name: str, gzip: bool = False):
    storage = 'fcz' if name.endswith('.fcz') else ('gzip' if gzip else 'plain')
    imports.entry({'name': name, 'storage': storage})
    if name.endswith('.fcz') and gzip:
        raise ValueError('FCZ + gzip storage is not supported')
    with imports.locked(component(repo)):
        path = imports.existing(repo, name, storage)
        if path is None:
            return PlainTextResponse('')
        return PlainTextResponse(hashlib.md5(imports.logical_bytes(path, storage)).hexdigest())


@app.get("/api/cache/get.php")
def get_cache(data_url: str, download: str = ""):
    path = inside(settings.CACHE_ROOT, b64decode(data_url).decode())
    if not path.is_file():
        raise FileNotFoundError(path.name)
    return FileResponse(path, media_type="application/octet-stream" if download else mime(path.name),
                        filename=path.name if download else None)


@app.get("/api/cache/clear.php")
def clear_cache(repo: str, force: str = ""):
    search.clear_browse(repo)
    return Response()


@app.api_route("/api/cache/update.php", methods=["GET", "POST"])
def update_cache():
    jobs.cleanup()
    for repo in search.datasets():
        search.clear_browse(repo)
        for sort in ("name", "plddt"):
            search.browse_cache(repo, sort)
    return Response()


@app.get("/api/plot/pae.php")
def pae_page(request: Request, data_url: str):
    # Generated legacy URLs may use the old internal hostname. Resolve their
    # /api/file path locally instead of making an arbitrary outbound request.
    path = urlsplit(b64decode(data_url).decode()).path
    from urllib.parse import unquote
    parts = path.split("/")
    if len(parts) != 5 or parts[1:3] != ["api", "file"] or not parts[4].endswith(".json"):
        raise ValueError("PAE data must reference a repository JSON file")
    repo, filename = unquote(parts[3]), unquote(parts[4])
    data = json.loads(read_file(repo, filename))
    matrix = data["pae"]
    if not isinstance(matrix, list) or not matrix:
        raise ValueError("No PAE matrix is available for this model")
    length = len(matrix)
    if any(not isinstance(row, list) or len(row) != length for row in matrix):
        raise ValueError("PAE matrix must be square")
    for row in matrix:
        for i, value in enumerate(row):
            try:
                value = float(value)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError("PAE values must be finite and non-negative") from exc
            if not math.isfinite(value) or value < 0:
                raise ValueError("PAE values must be finite and non-negative")
            row[i] = value
    try:
        maximum = float(data.get("max_pae", 31.75))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Maximum PAE must be finite and positive") from exc
    if not math.isfinite(maximum) or maximum <= 0:
        raise ValueError("Maximum PAE must be finite and positive")
    title = Path(filename).stem
    file_url = "/api/file/" + quote(repo, safe="") + "/" + quote(title, safe="")
    residues, warning = [], ""
    try:
        residues, warning = pae.residue_map(read_file(repo, title + ".cif"), length)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        logger.warning("Cannot map PAE residues for %s/%s: %s", repo, title, exc)
        warning = "The structure sequence could not be read. PAE remains available; linked selection is disabled."
    return render(request, "pae.html", {"title": title, "repo": repo, "pae_data": {
        "matrix": matrix, "maximum": maximum, "residues": residues, "warning": warning,
        "structure_url": file_url + ".cif?viewer=modern", "json_url": file_url + ".json",
    }})


@app.get("/salign/")
@app.get("/salign/index.php")
async def salign_page(request: Request):
    return render(request, "salign/index.html", await context(request))


@app.post("/api/salign/")
@app.post("/api/salign/index.php")
async def submit_salign(request: Request):
    form = await request.form(max_part_size=settings.MAX_BODY)
    structure = str(form.get("structure", ""))
    if not structure.strip():
        raise ValueError("Query structure required")
    hinge_input = str(form.get("hinge", "0"))
    if hinge_input not in tuple(str(value) for value in range(10)):
        raise ValueError("Hinge must be an integer between 0 and 9")
    hinge = int(hinge_input)
    threshold = float(form.get("tmscore", 0.5))
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("TM-score threshold must be between 0 and 1")
    repos = form.getlist("repo[]") or await run_in_threadpool(search.datasets)
    term = str(form.get("search", ""))
    if term:
        hits = await run_in_threadpool(search.search, repos, term)
        targets = [{"repo": hit["_index"], "name": hit["_source"]["name"]} for hit in hits]
    else:
        targets = []
        for repo in repos:
            targets.extend({"repo": repo, "name": name} for name in await run_in_threadpool(protein_names, repo))
    for target in targets:
        component(target["repo"])
        component(target["name"])
    rid = await run_in_threadpool(jobs.submit, structure, targets, hinge)
    return RedirectResponse("/salign/result.php?" + urlencode({"rid": rid, "tmscore": threshold}), status_code=302)


def decorate_salign(hit):
    repo, name, prefix = hit["repo"], hit["name"], hit["prefix"]
    hit["_view"] = {
        "Salign_Name": name, "Salign_Repo": repo,
        "Salign_Result_Viewer": "MP_" + hashlib.md5(prefix.encode()).hexdigest(),
        "Salign_Result_Path": "/api/file/" + quote(repo, safe="") + "/" + quote(name, safe="") + ".cif",
        "Salign_Query_Path": "/api/cache/get.php?data_url=" + token(prefix + ".pdb"),
        "PDB1_Path": token(hit["query"]), "PDB2_Path": token(hit["target"]),
        "Salign_Result_Data_URLs": {
            "hit": "/api/file/" + quote(repo, safe="") + "/" + quote(name, safe="") + ".pdb",
            **{key: token(prefix + suffix) for key, suffix in {
                "pdb": ".pdb", "pml": ".pml", "all": "_all.pml", "all_atm": "_all_atm.pml",
                "all_atm_lig": "_all_atm_lig.pml", "atm": "_atm.pml"}.items()}}}
    return hit


@app.api_route("/salign/result.php", methods=["GET", "POST"])
async def salign_result(request: Request, rid: str, tmscore: float = 0.5):
    directory = jobs.job_path(rid)
    if not directory.is_dir():
        raise FileNotFoundError(rid)
    status = await run_in_threadpool(jobs.status, directory)
    waiting = not (directory / "result.tar.gz").is_file()
    hits = await run_in_threadpool(jobs.results, rid, tmscore) if not waiting else []
    displayed, info = paginate(hits, await request.form(max_part_size=settings.MAX_BODY) if request.method == "POST" else {})
    values = {"Job_Status": status, "waiting": waiting, "Search_Result_Num": len(hits),
              "displayed": [decorate_salign(hit) for hit in displayed], "Page_Info": info,
              "Current_USalign_Num": int((directory / "progress.txt").read_text()),
              "Total_USalign_Num": max(1, int((directory / "total.txt").read_text())),
              "archive_token": base64.b64encode(f"MP_SALIGN_{rid}/result.tar.gz".encode()).decode()}
    return render(request, "salign/result.html", values,
                  headers={"Refresh": "5"} if waiting and status != "failed" else None)


@app.get("/salign/detail.php")
def salign_detail(request: Request, pdb1: str, pdb2: str):
    query = inside(settings.CACHE_ROOT, b64decode(pdb1).decode())
    target = inside(settings.CACHE_ROOT, b64decode(pdb2).decode())
    if not query.is_file() or query.name != "query.pdb":
        raise FileNotFoundError(query.name)
    repo, name = target.parent.name, target.stem
    hinge = jobs.job_hinge(query.parent)
    with tempfile.TemporaryDirectory(prefix="MP_SALIGN_DETAIL_") as temporary:
        restored = Path(temporary) / "hit.pdb"
        restored.write_bytes(read_file(repo, name + ".pdb"))
        result = subprocess.run([settings.USALIGN, str(query), str(restored), "-mm", "7", "-afp",
                                 "-hinge", str(hinge), "-fast"], capture_output=True, text=True,
                                check=True, timeout=settings.JOB_TIMEOUT)
    return render(request, "salign/detail.html", {"Details": result.stdout})


@app.api_route("/repo", methods=["GET", "HEAD"])
@app.api_route("/repo/{relative:path}", methods=["GET", "HEAD"])
def raw_repository(request: Request, relative: str = ""):
    path = inside(settings.REPO_ROOT, relative)
    if path.is_file():
        return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream")
    if not path.is_dir():
        raise FileNotFoundError(relative)
    links = []
    if relative.strip("/"):
        parent = str(Path(relative.rstrip("/")).parent)
        links.append('<li><a href="/repo/' + quote("" if parent == "." else parent, safe="/") + '/">../</a></li>')
    for child in sorted(path.iterdir()):
        # Do not expose symlink targets outside the repository root.
        if not child.resolve().is_relative_to(settings.REPO_ROOT):
            continue
        name = child.name + ("/" if child.is_dir() else "")
        url = "/repo/" + quote((relative.rstrip("/") + "/" + name).lstrip("/"), safe="/")
        links.append(f'<li><a href="{html.escape(url, quote=True)}">{html.escape(name)}</a></li>')
    return HTMLResponse("<!doctype html><title>Index of /repo/" + html.escape(relative) + "</title><ul>" + "".join(links) + "</ul>")
