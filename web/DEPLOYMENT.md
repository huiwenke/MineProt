# Python deployment

The browser assets and legacy URLs (including `.php`) are served by Python.
PHP, PHP-FPM, Nginx and MAXIT are not required. Old files under `config/php`
and `config/nginx` are inactive and are retained for reference.

## Docker

From the project root, run `toolkit/setup.sh -p 80 -d ./data`.
Cache defaults to `/tmp/mineprot` inside the Web container. To use shared
memory, add `-s 1024` for a 1024 MiB `/dev/shm` mount and cache at
`/dev/shm/mineprot`. `-s 0` switches back to `/tmp`. The setting is retained
in `.env` as `MP_CACHE_SHM_MB`; command-line options override it.
Before building, setup rejects invalid sizes or requests exceeding the local
host's `/dev/shm` total/free capacity, available RAM, or cgroup memory limit.
These checks target a local container engine. The shared-memory size is a
filesystem ceiling, not reserved RAM; later memory pressure or a full cache
can still cause a task to fail. Cache contents in shared memory are lost when
the container is stopped; neither cache mode is preserved on recreation.
The script builds and starts `web` and `es`; it does not delete existing data.
The bundled Foldcomp and US-align executables require Linux x86-64.
Image building runs in the foreground. Setup starts Elasticsearch in detached
mode and explicitly waits up to 180 seconds for yellow/green cluster health,
then starts Web without a second Compose dependency wait and checks `/healthz`
for up to 180 seconds. On timeout it prints container status and the affected
container's last 100 log lines and exits with an error. Containers are left
available for diagnosis. Setup does not follow logs after a successful start.
Base image names include their registry to avoid Podman short-name prompts.
For Podman, setup builds directly with the engine to avoid Compose provider
pull-policy differences. It checks Docker Hub, localhost and short-name local
aliases for each base image, then uses `--pull=never` when one exists. Only
missing base images are downloaded. Podman builds use Docker image format so
image HEALTHCHECK instructions are retained. Compose uses explicit output names.
Local images must belong to the same engine, connection and user running setup;
Docker images and rootful Podman images are not visible to rootless Podman.

Application sources and assets are copied into the image. After editing them,
rebuild with `docker compose up -d --build`. The setup command also rebuilds.
Old nginx/php containers are removed by Compose's `--remove-orphans` option.
The original US-align archive is retained, including local changes, under
`app/bin/`; that directory name does not imply a runtime PHP dependency.

The setup script verifies `app/python/tools.sha256` before building. If a
Foldcomp download no longer matches the pinned local archive, setup stops.
Obtain the matching archive, or review and explicitly update its checksum
before deploying a different version. Do the same when updating US-align.
An archive must contain the root-level `foldcomp` or `USalign` executable.

Data directories:

- `repo/`: existing repository data, unchanged format.
- `es/`: existing Elasticsearch 7.12.1 data, unchanged version and IK plugin.
- Cache: Python browse caches and Salign tasks in the container's `/tmp` or
  `/dev/shm`; the old host `cache/` directory is no longer mounted or required.

Browse displays 1000 proteins per page. On cache rebuild it reads metadata via
Elasticsearch `_mget` in batches of 500, reusing one HTTP connection pool and
caching both sort orders. Cache hits check the repository directory timestamp
without scanning every file. Directory changes and application API writes
invalidate the cache; direct edits to existing files or ES documents are picked
up within five minutes or immediately after clicking Refresh.

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
ModelCIF pLDDT categories and missing standard chemical component types for
PDBe Mol* 1.2.1. AF2 PDB B-factors are interpreted as pLDDT specifically by this
AF2 endpoint; experimental structures should be supplied as CIF instead.
Generated CIFs and CIF viewing responses omit hydrogen atoms, including D/T
isotopes, together with their anisotropic records and atom-type entries.
Existing repository files are not rewritten.

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

The viewing endpoint also repairs missing standard residue types in existing
CIFs and removes the erroneous `MineProt` database marker added by earlier
conversions, preserving real database records. That marker makes this viewer
assume a PDB archive model and skip automatic secondary structure calculation.
The explicit AF confidence theme does not require it. Secondary structure is
computed by the existing browser plugin; no external DSSP program is required.
For viewing copies containing only standard amino acid components with ordinary
peptide linking types, the chemical component table is omitted so Mol* uses its
complete built-in definitions. A partial Gemmi table otherwise disables that
fallback, and missing standard-residue flags add ball-and-stick geometry over
the cartoon. Tables containing custom components are retained.

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
