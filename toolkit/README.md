# MineProt toolkit

A Python 3.12+ package for preparing predictions and importing protein data.
The complete [toolkit manual](../docs/Toolkit-manual.md) covers single imports,
ColabFold monomers, AlphaFold3 complexes, batch imports, 3D-Beacons preparation
and MSA Neff calculation. Server setup is in the
[deployment manual](../docs/Deployment-manual.md).

## Installation

From the project root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ./toolkit
mineprot-toolkit --help
```

Use `python -m pip install ./toolkit` for a regular installation.
Dependencies are declared in `pyproject.toml`; the old
`scripts/requirements.txt` no longer exists. Foldcomp operations require the
pinned package and a compatible wheel. Neff calculation additionally needs
an external `calNf` executable, provided separately.

## Code organization

- `src/mineprot_toolkit/` holds implementations and shared `common/` modules.
- `scripts/` holds thin source-checkout entrypoints sharing `_run.py`.
- `ai/` groups system-specific commands; `batch/` contains `import_es`,
  `import_repo` and `prepare_beacon`; `misc/` holds other utilities.
- `import_single.py` is a standalone command alongside these groups.
- `tests/` contains offline regression checks.
- `plugins/` contains the JavaScript integrations documented in the manual.

Installed commands and checkout scripts accept the same arguments:

```bash
mineprot-toolkit batch import-repo --help
python toolkit/scripts/batch/import_repo.py --help
python -m mineprot_toolkit --help
```

New Python commands should implement `main(argv=None)` without parsing CLI
arguments, writing files, making network requests or starting workers on
import. Register commands in `src/mineprot_toolkit/cli.py`, and keep script
entrypoints thin. Edit shared behavior in the package rather than copying it
into scripts. Shell import pipelines resolve scripts relative to themselves.

## Development

```bash
python -m pip install -e './toolkit[dev]'
ruff check toolkit
ruff format --check toolkit
python -m unittest discover -s toolkit/tests -v
python -m build toolkit
```

Tests use temporary files and mocked HTTP/subprocess calls; no deployed
server, UniProt access, container engine or real `calNf` is required. CI runs
these checks with Python 3.12. Keep this README for package installation and
development; maintain user workflows in `docs/Toolkit-manual.md`.
