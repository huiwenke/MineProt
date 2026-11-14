# MineProt Deployment Manual

MineProt's current Web service uses **Python 3.12, FastAPI and Uvicorn**.
Gemmi handles structure conversion, US-align performs alignment and the
Foldcomp Python package decodes FCZ. Elasticsearch and the bundled IK plugin
remain at **7.12.1**. Legacy `.php` URLs are served by Python; PHP, PHP-FPM,
Nginx and MAXIT are not required. Old `config/php` and `config/nginx` files
are inactive references.

## 1. Prerequisites

Use a Linux x86-64 host with Bash and either Docker with Docker Compose, or
Podman with a working Compose provider. Setup checks the engine architecture.
Run setup and Compose commands from the project root.

You need `sha256sum`, sufficient disk space and memory, and access to container
registries, OS package repositories and PyPI during builds. Elasticsearch uses
a 512 MiB JVM heap plus additional memory; Web, file conversion and alignment
jobs need their own capacity. Local base images alone do not make a build offline.

The checkout must include:

```text
app/bin/usalign.tar.xz
app/python/tools.sha256
web/requirements.txt
```

The US-align archive must contain a root-level `USalign` executable. Setup
verifies its SHA-256 before building; review its source/version before changing
the checksum. **Foldcomp 1.0.0 is installed from PyPI as a binary Python wheel**;
no Foldcomp executable, archive or setup-time archive download is required.
The Web build installs only binary wheels and fails if a compatible wheel is
unavailable. A leftover `app/bin/foldcomp.tar.gz` is ignored.

## 2. Start the services

### Development or a writable internal server

```bash
cd /path/to/MineProt
bash toolkit/setup.sh -c docker -p 8080 -d /absolute/path/to/mineprot-data --development
```

Open `http://localhost:8080`, or replace localhost with the server address.
Development exposes a writable Web service. The default setup mode is
`development`; subsequent runs retain the mode saved in `.env`.

### Production: public read-only access and local management

```bash
bash toolkit/setup.sh -c docker -p 8080 -d /absolute/path/to/mineprot-data --production
```

Production starts two Web processes sharing repository files and Elasticsearch:

| Service | Address in this example | Access |
| --- | --- | --- |
| `web` / `MineWeb` | Public host port `8080` | Read-only application with a read-only repository mount. |
| `admin` / `MineAdmin` | `127.0.0.1:8081` on the deployment server | Writable management application. |

Use `-a PORT` to change the management port; it must differ from the public
port. Public Web rejects imports, import preflight, Elasticsearch add/delete,
the import page, and explicit cache clear/rebuild with **HTTP 403**, regardless
of method or forwarded client IP. Search, Browse, downloads, structure
conversion and Salign remain available, including their temporary caches.
Elasticsearch has no published host port.

Toolkit defaults to the management address. Run it on the server or use:

```bash
ssh -N -L 8081:127.0.0.1:8081 user@server
```

Do not expose the management service through a public reverse proxy. MineProt
has no built-in API authentication; provide TLS/access control at the proxy
when needed. `--development` restores writable public access and removes the
separate management container without deleting repository or ES data.

### What setup does

1. Validate arguments, engine architecture and US-align checksum.
2. Create `repo/` and, if absent, copy the bundled ES initialization directory
   into `es/` under the data root.
3. Update managed entries in project-root `.env`, preserving other entries.
4. Build images in the foreground, then start Elasticsearch detached.
5. Wait up to 180 seconds for yellow/green ES health, then start Web and,
   in production, management.
6. Check each Web process's `/healthz` for up to 180 seconds.

Yellow is accepted for a single-node ES cluster. On timeout, setup prints
container status and the affected container's last 100 log lines, leaves the
containers available for diagnosis and exits with an error. On success it
exits without following logs. `/healthz` checks Web-process liveness, not
Elasticsearch or US-align functionality.

### Setup options

| Option | Default | Meaning |
| --- | --- | --- |
| `-c ENGINE` | `docker` | Docker or Podman. |
| `-p PORT` | `80` | Public Web port, 1–65535. |
| `-d PATH` | `./data` | Data root containing `repo/` and `es/`. |
| `-s MIB` | `0` | Public Web shared-memory cache size; 0 uses `/tmp`. |
| `-a PORT` | `8081` | Local production management port, 1–65535. |
| `--production` | Off initially | Read-only public Web plus local management. |
| `--development` | On initially | Writable public Web. |
| `-h` | — | Show usage. |

Explicit options override supported settings in `.env`, which override
initial defaults. Omitted port, engine, data, cache, mode and management-port
options retain their saved settings. Data paths cannot contain single quotes
or newlines.

### Podman

```bash
podman info
podman compose version
bash toolkit/setup.sh -c podman -p 8080 -d /absolute/path/to/mineprot-data --production
```

Setup first tries the engine's `compose` subcommand, then `podman-compose`.
For rootless Podman, use an unprivileged port such as 8080. Keep the same
user and engine connection for maintenance: Docker, rootful Podman and
rootless Podman have separate image stores.

Podman builds run directly through the engine, using Docker image format to
retain HEALTHCHECK instructions. Setup checks registry-qualified, localhost
and short-name aliases for base images, uses `--pull=never` for a local image,
and downloads missing base images. On SELinux hosts, inspect mount access
denials and configure suitable labels/policies; Compose mounts do not include
`:z` or `:Z`. Disabling SELinux is not a project prerequisite.

## 3. Persistent data and temporary caches

```text
mineprot-data/
├── repo/    # Persistent structures and companion files
└── es/      # Persistent Elasticsearch 7.12.1 data
```

Pass the parent directory to `-d`. Repository files are mounted at
`/var/www/data` in Web. Setup uses the invoking user's UID/GID for both Web
processes, checks that the repository directory is writable, and does not
recursively change ownership. Existing files must be readable and writable
where management imports require it. ES retains its image user and its own
data-directory permission requirements. Back up both `repo/` and `es/`.

Browse and Salign caches normally live at `/tmp/mineprot` inside each Web
container. They are not host mounts and are lost on container recreation.
Download alignment results that must be retained. The old host `cache/`
directory is no longer required.

### Shared-memory cache

```bash
bash toolkit/setup.sh -s 1024
# Return to the temporary filesystem cache:
bash toolkit/setup.sh -s 0
```

With `-s 1024`, public Web gets a 1024 MiB `/dev/shm` ceiling and cache path
`/dev/shm/mineprot`. Setup checks local `/dev/shm` total/free capacity,
available RAM and cgroup limits. This is a filesystem ceiling, not reserved
RAM; later memory pressure or a full cache can still fail jobs. These checks
assume a local engine. Shared-memory contents are lost on container stop.
The production management service always uses its own `/tmp/mineprot` cache
and 64 MiB shared-memory setting.

### Browse behavior

Browse shows 1000 proteins per page. Cache rebuilds fetch metadata using
ES `_mget` batches of 500 and retain both name and pLDDT orderings. API writes
invalidate the writing process's cache. Repository directory changes are
noticed immediately; direct replacement of existing files and ES-only changes
are reflected within five minutes or after a writable service's Refresh.
Production public Web and management have separate caches. Refreshing the
management cache does not clear public Web's cache, and public Web blocks
explicit Refresh/cache-management requests.

## 4. Configuration

Setup manages these project-root `.env` entries:

```text
MP_PORT MP_DATA MP_CE MP_UID MP_GID
MP_CACHE_SHM_MB MP_CACHE_PATH MP_SHM_SIZE_MB
MP_MODE MP_ADMIN_PORT MP_READ_ONLY MP_REPO_ACCESS COMPOSE_PROFILES
```

Production sets `MP_READ_ONLY=true`, `MP_REPO_ACCESS=ro` and
`COMPOSE_PROFILES=production` for public Web. The management process explicitly
uses writable settings. Application variables are read at process startup:

| Variable | Application default | Current Compose behavior |
| --- | --- | --- |
| `MP_REPO_PATH` | `<project>/data/repo` | `/var/www/data` in both services. |
| `MP_ELASTICSEARCH` | `http://elasticsearch:9200` | Same internal address. |
| `MP_CACHE_PATH` | `/tmp/mineprot` | Setup-managed for public Web; fixed `/tmp/mineprot` for management. |
| `MP_READ_ONLY` | `false` | Setup-managed for public Web; fixed `false` for management. Accepts `true`/`false`. |
| `MP_MAX_BODY_BYTES` | `104857600` (100 MiB) | Fixed to this value in both services. |
| `MP_SALIGN_CONCURRENCY` | `2` | Passed from `.env` to public Web; management uses the default. |
| `MP_SALIGN_TIMEOUT` | `300` seconds per invocation | Passed from `.env` to public Web; management uses the default. |
| `MP_FOLDCOMP_TIMEOUT` | `300` seconds | Passed from `.env` to both services. |
| `MP_USALIGN` | `USalign` | Application-supported; not explicitly passed by Compose. |

`MP_FOLDCOMP` is no longer used. Adding a variable to `.env` alone does not
pass it into a container unless Compose references it. Edit Compose when
overriding a fixed value or adding an application variable.

## 5. Updating and troubleshooting

The image contains Web sources, and the current Compose configuration also
bind-mounts `./web:/app/web:ro`. Template/static edits are therefore visible
from the checkout. Templates normally reload; Python changes require a Web
process/container restart. Rebuild for changed dependencies/binaries and for
updated standalone images. Running setup again rebuilds with saved options:

```bash
bash toolkit/setup.sh
# Inspect current services and recent output:
docker compose ps
docker compose logs --tail 100 web es
# In production, inspect management too:
docker compose logs --tail 100 admin
```

Setup removes obsolete Compose containers through `--remove-orphans`, keeps
data directories, and checks readiness. Do not remove data to troubleshoot a
startup failure. A missing model in Search can mean files were uploaded without
metadata, or metadata was indexed without files: these are separate operations.
See the [toolkit manual](Toolkit-manual.md) for both import stages, modes,
format conflicts and examples for monomers and complexes.

## 6. Without containers

Install Python 3.12 and `web/requirements.txt`. Run ES 7.12.1 with matching IK
separately, and provide US-align on PATH or through `MP_USALIGN`:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r web/requirements.txt
cd web
MP_REPO_PATH=/absolute/path/to/data/repo \
MP_CACHE_PATH=/absolute/path/to/data/cache \
MP_ELASTICSEARCH=http://127.0.0.1:9200 \
uvicorn mineprot.app:app --host 0.0.0.0 --port 8000 --workers 1
```

For production, set `MP_READ_ONLY=true` on the public process, enforce read-only
repository permissions, and run a separate writable process bound to
`127.0.0.1` for management. Give the two processes separate cache directories.
No Redis or separate task service is required. Salign concurrency is bounded
across workers sharing a cache; each US-align invocation has its own timeout.
Jobs lost on restart are marked failed when their result page is opened;
submit a new query to retry.

## 7. Structure viewing and alignment

Search, PAE and Salign use the vendored **PDBe Mol* 3.12.0** bundle, with theme
switching. Salign displays the transformed query in gray and keeps the target's
default pLDDT display; both are visible initially. It counts polymer chains in
the first model of each structure. If either has multiple polymer chains, it
uses `-mm 1 -fast`; otherwise `-mm 7 -afp -hinge N -fast`. Water/ligand-only
chains and extra models do not trigger complex mode. Detail uses the same rule.

The current viewers request CIF with `?viewer=modern`. Legacy callers without
that parameter still receive the legacy viewing adapter. Stored coordinates
and repository files are not rewritten by viewing; `/repo/` serves original
bytes. PDB-to-AlphaFold-style CIF conversion treats B-factors as prediction
pLDDT, adds ModelCIF/sequence information and removes hydrogen/D/T atoms.
Prefer original CIF for experimental structures and complexes. FCZ decoding
runs in an isolated Python worker; malformed data returns 400 and decoder
timeouts return 502 without crashing Web.

PAE reads local repository JSON, displays an interactive matrix and links
unambiguous residue/token selections to the structure. AF3 token metadata can
map multichain and non-protein components. Missing/ambiguous mappings disable
linking for affected positions rather than selecting an unrelated residue.
See the [API manual](API-manual.md#10-pae-visualization) for the JSON contract.

## 8. Local validation

With Python 3.12 and Web dependencies installed, run from the project root:

```bash
PYTHONPATH=web python -m unittest discover -s web/tests -v
```

These tests need no running ES or container engine and do not replace checking
a real deployment. Toolkit checks are in [toolkit/README.md](../toolkit/README.md#development).
Dependency notices remain in [web/THIRD_PARTY.md](../web/THIRD_PARTY.md), with
vendored bundle provenance beside its assets.
