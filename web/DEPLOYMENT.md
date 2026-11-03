# Python deployment

The browser assets and legacy URLs (including `.php`) are served by Python.
PHP, PHP-FPM, Nginx and MAXIT are not required. Old files under `config/php`
and `config/nginx` are inactive and are retained for reference.

## Docker

From the project root, run `toolkit/setup.sh -p 80 -d ./data`.
The script builds and starts `web` and `es`; it does not delete existing data.
The bundled Foldcomp and US-align executables require Linux x86-64.

Application sources and assets are copied into the image. After editing them,
rebuild with `docker compose up -d --build`. The setup command also rebuilds.
Old nginx/php containers are removed by Compose's `--remove-orphans` option.
The original US-align archive is retained, including local changes, under
`app/php/`; that directory name does not imply a runtime PHP dependency.

The setup script verifies `app/python/tools.sha256` before building. If a
Foldcomp download no longer matches the pinned local archive, setup stops.
Obtain the matching archive, or review and explicitly update its checksum
before deploying a different version. Do the same when updating US-align.
An archive must contain the root-level `foldcomp` or `USalign` executable.

Data directories:

- `repo/`: existing repository data, unchanged format.
- `es/`: existing Elasticsearch 7.12.1 data, unchanged version and IK plugin.
- `cache/`: new Python browse caches and Salign tasks, preserved on restart.

The setup script runs the Web container with the invoking user's UID/GID.
Existing repository files must be readable, and writable for imports. It does
not recursively change data ownership. Elasticsearch keeps its original image
user and its existing directory permission requirements.

## Without Docker

Use Python 3.12, install `web/requirements.txt`, and make `foldcomp` and
`USalign` available on PATH. Run an Elasticsearch 7.12.1 instance with the
project's matching IK plugin separately. From `web/`, run:

```sh
MP_REPO_PATH=/absolute/path/to/data/repo \
MP_CACHE_PATH=/absolute/path/to/data/cache \
MP_ELASTICSEARCH=http://127.0.0.1:9200 \
uvicorn mineprot.app:app --host 0.0.0.0 --port 8000 --workers 1
```

`MP_SALIGN_CONCURRENCY` (default 2) bounds simultaneous alignment jobs across
Web workers. `MP_SALIGN_TIMEOUT` (default 300) limits each US-align invocation.
`MP_MAX_BODY_BYTES` (default 104857600) limits uploads, including decompressed
import JSON. No Redis or separate task service is required. Active jobs lost
during a container restart are marked failed when their result page is opened;
completed results remain downloadable. Submit a new query to retry a failed job.

## Structure compatibility

`/api/pdb2alphacif/` uses Gemmi and adds missing observed polymer sequences,
ModelCIF pLDDT categories and the database identifier required by the bundled
PDBe Mol* 1.2.1. AF2 PDB B-factors are interpreted as pLDDT specifically by this
AF2 endpoint; experimental structures should be supplied as CIF instead.

The original author numbering is retained in stored files and conversion
responses. `/api/file/...cif` returns a viewing copy for single-polymer-entity
predictions, with author numbering aligned to label numbering, because the old
viewer's confidence reader uses the wrong numbering namespace. `/repo/...`
serves the original file unchanged. Raw `.gz` files under `/repo/` stay compressed;
the `/api/file/` endpoints transparently decompress them as before.

The old viewer hardcodes entity 1, so multiple distinct polymer entities are
not guaranteed to receive complete confidence coloring without a frontend
change. Their entity relationships are preserved. This migration does not
upgrade the viewer. Existing CIF quality categories are retained.

The PAE endpoint resolves legacy repository JSON URLs locally. It does not
fetch arbitrary external URLs. Downloads are confined to repository/cache roots.

## Validation status

No tests, service starts, dependency installation or image builds were run as
part of this migration, at the user's request. Suggested manual coverage:
existing toolkit imports (including gzip/force), search and pagination, browse
sort/refresh, all file fallbacks, AF2 sequence and pLDDT colors/tooltips, PAE,
Salign progress/failure/detail/archive, and existing-data Docker startup.

See `THIRD_PARTY.md` for license and source information. The repository-root
README describes the former PHP deployment; use this document for Python.
