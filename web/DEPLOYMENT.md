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
The bundled US-align executable requires Linux x86-64. Foldcomp 1.0.0 is
installed from PyPI with the Python dependencies using a prebuilt wheel for
Python 3.12 on Linux x86-64. No Foldcomp executable or separate archive download
is required.
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

The setup script verifies the US-align archive against `app/python/tools.sha256`
before building. Review and update its checksum when replacing the archive,
which must contain the root-level `USalign` executable. Foldcomp's version is
pinned in `web/requirements.txt`; image builds install only binary wheels and
fail if no compatible wheel is available. A leftover `app/bin/foldcomp.tar.gz`
from an older deployment is ignored and excluded from the Web build context.

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

## Production: public read-only access and local management

```sh
bash toolkit/setup.sh -c docker -p 8080 -d ./data --production
```

Production starts a read-only `web` service and a writable `admin` service
bound to `127.0.0.1:8081` on the deployment server. Use `-a PORT` to change
the management port. The mode and ports are saved in `.env`; subsequent setup
runs retain them. `--development` restores the original writable public Web
and removes the separate management container, without removing its repository
or Elasticsearch data.

Public Web rejects repository imports (including batch/check and legacy aliases),
Elasticsearch add/delete operations, the import page, and explicit cache
clear/rebuild requests with HTTP 403, regardless of HTTP method or forwarded
client IP. Its repository mount is read-only. Search, browsing, downloads,
conversions and Salign remain available; their temporary cache stays writable.
Elasticsearch has no published host port. Do not publish the management service
through a public reverse proxy.

Toolkit scripts default to `http://127.0.0.1:8081`, including conversion helpers
and the interactive importer. Run them on the deployment server, or create an
SSH tunnel from your workstation:

```sh
ssh -N -L 8081:127.0.0.1:8081 user@server
```

For a custom management port or a development deployment, supply `--url`
explicitly. Batch import example:

```sh
python toolkit/scripts/batch/import_repo.py -i /path/to/models -n proteins \
  --url http://127.0.0.1:8081/api/import2repo/
```

Web and management use separate temporary caches. Repository directory changes
invalidate browse caches immediately; index-only updates and replacement of
existing files appear within five minutes. Refreshing the management cache
does not clear the public service's cache.

Setup manages `MP_READ_ONLY=true`, `MP_REPO_ACCESS=ro` and
`COMPOSE_PROFILES=production` in production, with the opposite settings in
development. Without containers, set `MP_READ_ONLY=true` for the public process
and run a separate writable process bound to `127.0.0.1` for management. Also
enforce read-only repository permissions for the public process.

Regression checks (no running Elasticsearch or container engine required):

```sh
PYTHONPATH=web python -m unittest discover -s web/tests -v
```

## Without Docker

Use Python 3.12, install `web/requirements.txt` (including Foldcomp), and make
`USalign` available on PATH or set `MP_USALIGN` to its executable path.
`MP_FOLDCOMP` is no longer used. Run an Elasticsearch 7.12.1 instance with the
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

## Batch repository imports

Upgrade the Web service before using the new `toolkit/scripts/batch/import_repo.py`.
The toolkit requires Python 3.12+. Install it with
`python -m pip install -e ./toolkit` from the project root; dependencies,
including Requests and Foldcomp 1.0.0, are declared in its `pyproject.toml`.
See the [toolkit guide](../toolkit/README.md) for grouped commands and migration. Example commands from the project root:

```sh
# Store ordinary local PDBs as gzip on the server.
python toolkit/scripts/batch/import_repo.py -i /path/to/models -n proteins -m 3 -z
# Compress single-chain local PDBs to FCZ and store FCZ directly.
python toolkit/scripts/batch/import_repo.py -i /path/to/models -n proteins -m 4
```

Use `--url http://HOST/api/import2repo/` for a remote server. Modes 0..3 retain
their file selection rules, including `.a3m` in mode 0. Local files are read as
bytes and are never rewritten. Mode 4 ignores non-PDB files; unsupported or
multichain PDBs are reported as failed, without an automatic fallback.

Each batch uses `POST /api/import2repo/batch/check` for a JSON manifest and
`POST /api/import2repo/batch` for multipart binary data. The defaults are at most
256 files, a target of 16 MiB including estimated multipart overhead, and two
concurrent batches. Tune `--batch-files`, `--batch-mib` and `--workers` (1..8).
A single larger file is sent alone, subject to the server limit. The server
advertises its body limit during preflight; clients split uploads further when
needed. Connections are reused; transient request failures are retried. Old
servers are reported as unsupported instead of silently using individual uploads.

Ordinary files use gzip for transport independently of `-z`, which selects
gzip storage. Content hashes are calculated over the uncompressed bytes so a
local PDB and its server-side `.pdb.gz` verify correctly. FCZ uses raw binary
transport and storage. Its byte SHA-256 verifies transport; an additional hash
of the PDB decoded from FCZ verifies equivalent FCZ content. Foldcomp output
bytes can vary between identical compressions, so raw FCZ hashes alone cannot
reliably detect unchanged structures. The decoded hash compares two FCZ outputs,
not the original PDB against its lossy reconstruction.

Storage formats must agree. Server gzip requires `-z`; server FCZ requires
`-m 4`; server plain files require the ordinary mode without `-z`. `-m 4 -z`
is rejected locally. New `.fcz.gz` imports are rejected, and an existing
`.fcz.gz` or multiple same-name PDB/FCZ variants are reported as conflicts.
`-f` permits replacing different content in the same format only. Identical
content is skipped; different existing content without `-f` is reported as
`exists` and skipped. Format conflicts are errors even with `-f`.

The old single-file URLs remain available and enforce the same storage-format
rules. Legacy `check.php` accepts `gzip=true` to check decompressed gzip content.

Uploads are length/hash checked and atomically committed per file; a failed file
does not roll back successful files in the batch. Upload commits recheck server
state under repository locks, and retries recognize completed content. FCZ
validation reuses an isolated Python process per batch and replaces it after a
native crash or timeout. Request bodies spill to temporary disk after 1 MiB,
and multipart uploads are closed after processing. Temporary storage must have
room for concurrent batches. Browse caches are cleared once per changed batch.
The CLI prints per-file outcomes and a summary, and exits nonzero for failures.

## Structure compatibility

Search, PAE and Salign result viewers use the vendored PDBe Mol* 3.12.0 bundle.
Salign loads the US-align-transformed query as a gray overlay and retains the
target's default pLDDT display. Both structures are visible initially, with
sequence panels and viewer controls available. Theme changes preserve the
alignment, colors and camera.

For each Salign pair, the backend counts polymer chains in the first model of
both structures. If either contains more than one polymer chain, US-align uses
`-mm 1 -fast`; otherwise it uses `-mm 7 -afp -hinge N -fast`. Water and
non-polymer ligand chains do not trigger complex mode, and multiple models are
not counted as separate chains. The Detail view uses the same selection rule.
The hinge field's info symbol and help text explain that hinge is ignored for
complex alignments.

FCZ conversion and repository fallbacks use the Foldcomp Python API in a spawned
Python worker, without temporary FCZ/PDB files or a standalone Foldcomp
executable. Foldcomp 1.0.0 can crash on malformed FCZ data and holds the GIL;
isolating each conversion keeps native crashes and decoding work out of the
Web process. The existing FCZ upload URLs and PDB response format are retained.
Invalid FCZ inputs, including decoder crashes, return HTTP 400. Set
`MP_FOLDCOMP_TIMEOUT` (default 300 seconds) to bound each conversion, including
worker startup; a timeout terminates the worker and returns HTTP 502.
`MP_SALIGN_TIMEOUT` continues to control US-align only.

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

Batch import regression tests cover gzip content verification, strict format
conflicts, same-format overwrite, retries, integrity failures, partial success,
request limits, FCZ native crash/timeout recovery, and real CLI-to-Web imports
including repeated FCZ compression. Run with Python 3.12, Web dependencies and
Requests installed:

```sh
PYTHONPATH=web python -m unittest discover -s web/tests -v
```

The upstream test fixture and its MIT license are in `tests/fixtures/`.
These focused tests do not exercise Elasticsearch, the full setup script against
existing data, or the complete Salign/browser workflows.

See `THIRD_PARTY.md` for license and source information, and the repository-root
README for the project overview.
