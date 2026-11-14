# MineProt toolkit

A Python 3.12+ package for preparing predictions, importing repositories and
processing protein datasets. It is separate from the Web service package.

From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ./toolkit
mineprot-toolkit --help
```

Use `python -m pip install ./toolkit` for a regular installation. Dependencies
and optional development tools are declared only in `pyproject.toml`; the old
`scripts/requirements.txt` has been removed. FCZ operations require the pinned
Foldcomp version and a platform with a compatible wheel. `calNf` is an external
executable, supplied separately via PATH or `--cal-nf /path/to/calNf`.

## Layout

```text
toolkit/
├── pyproject.toml
├── scripts/                        # Source-checkout entrypoints
│   ├── ai/
│   │   ├── alphafold2/              # Transform and import pipeline
│   │   ├── alphafold3/              # Complex/pair preparation, ipTM selection
│   │   └── colabfold/               # Transform and import pipeline
│   ├── batch/                      # import_es, import_repo, prepare_beacon
│   ├── import_single.py            # Standalone interactive importer
│   └── misc/                       # Other processing and conversion tools
├── src/mineprot_toolkit/            # All Python implementations
│   ├── ai/                         # System-specific processing
│   ├── batch/                      # Repository and metadata batch imports
│   ├── import_single.py            # Standalone interactive importer
│   ├── misc/                       # Other commands
│   ├── common/                     # HTTP, uploads, annotation, naming and I/O
│   └── cli.py                      # Installed command dispatch
└── tests/                          # Offline regression checks
```

Python files in `scripts/` are thin entrypoints, not duplicate implementations.
They locate the local package through one bootstrap helper, so they can be run
from any working directory. Implementation modules use package imports and
`main(argv=None)`; importing them does not parse CLI arguments, create output
folders, send network requests or start worker threads.

## Commands

Installed commands and source-checkout scripts take the same arguments:

```bash
mineprot-toolkit batch import-repo -i /path/to/models -n demo
python toolkit/scripts/batch/import_repo.py -i /path/to/models -n demo

mineprot-toolkit import-single
mineprot-toolkit import-single -i saved_import.json -f

mineprot-toolkit ai alphafold3 prepare-complex --help
mineprot-toolkit misc extract-plddt -i /path/to/models
mineprot-toolkit misc calculate-neff --a3m /path/to/msas --cal-nf /path/to/calNf
```

Run `mineprot-toolkit ai --help`, `mineprot-toolkit batch --help` or
`mineprot-toolkit misc --help` to list commands; append `--help` to any command
for its arguments. The Python invocation `python -m mineprot_toolkit` is also
supported.

The two end-to-end AI import pipelines remain Bash entrypoints in the checkout:

```bash
bash toolkit/scripts/ai/colabfold/import.sh /path/to/results \
  --repo demo --zip --relax --python "$(command -v python)"
bash toolkit/scripts/ai/alphafold2/import.sh /path/to/results \
  --repo demo --python "$(command -v python)"
```

They resolve other scripts relative to their own location, quote paths and
arguments, stop when a step fails and clean their temporary directory on exit.
Logs remain in the temporary-files directory for diagnosis. `--scripts-dir`
accepts the categorized `toolkit/scripts` directory if an override is needed.

The default server URL remains **http://127.0.0.1:8081**, the production
management endpoint. Supply `--url` for a different port or a development Web
service. The batch repository command expects the full endpoint, e.g.
`--url http://127.0.0.1:8080/api/import2repo/`; AI import pipelines and the
interactive importer expect the base URL. Run on the server or through an SSH
tunnel. Reorganization does not change the server's API URLs or storage format.

The standalone importer is also available as `python toolkit/scripts/import_single.py`.
`batch/` contains only `import_es`, `import_repo` and `prepare_beacon`; other
general-purpose processing commands live in `misc/`.

## Migration from the old script paths

Paths below are relative to `toolkit/scripts/`. Old paths were removed; update
saved shell commands and external automation to use the new paths or installed
commands. Existing interactive-import JSON configuration files remain valid.

| Old script | New script | Installed command after `mineprot-toolkit` |
| --- | --- | --- |
| `alphafold2/transform.py` | `ai/alphafold2/transform.py` | `ai alphafold2 transform` |
| `alphafold2/import.sh` | `ai/alphafold2/import.sh` | Bash pipeline |
| `colabfold/transform.py` | `ai/colabfold/transform.py` | `ai colabfold transform` |
| `colabfold/import.sh` | `ai/colabfold/import.sh` | Bash pipeline |
| `alphafold3/pre4complex.py` | `ai/alphafold3/prepare_complex.py` | `ai alphafold3 prepare-complex` |
| `alphafold3/pre4pair.py` | `ai/alphafold3/prepare_pair.py` | `ai alphafold3 prepare-pair` |
| `alphafold3/selectMax.py` | `ai/alphafold3/select_max.py` | `ai alphafold3 select-max` |
| `import2repo.py` | `batch/import_repo.py` | `batch import-repo` |
| `import2es.py` | `batch/import_es.py` | `batch import-es` |
| `export.py` | `misc/export.py` | `misc export` |
| `pre4beacon.py` | `batch/prepare_beacon.py` | `batch prepare-beacon` |
| `calNf.py` | `misc/calculate_neff.py` | `misc calculate-neff` |
| `2plddt.py` | `misc/extract_plddt.py` | `misc extract-plddt` |
| `selectMax.py` | `misc/select_max.py` | `misc select-max` |
| `random2box.py` | `misc/distribute_files.py` | `misc distribute-files` |
| `ppdb/2cif.py` | `misc/convert_pdb.py` | `misc convert-pdb` |
| `ppdb/transform.py` | `misc/preprocess_pdb.py` | `misc preprocess-pdb` |
| `import_single.py` | `import_single.py` | `import-single` |

`ppdb` processes generic predicted PDBs, so it belongs in `misc/` rather than
under a particular AI system. Shared library modules moved into
`mineprot_toolkit.common`: `api`, `annotations` (formerly `annotate.py`),
`sequences` (formerly `pdb2seq.py`), `naming` (formerly `rename.py`) and `uploads`
(the transport code formerly embedded in `import2repo.py`). Helper function
names now use snake_case. Runtime JSON fields and the existing CLI flags are
preserved; `--calNf` remains an alias for the new spelling `--cal-nf`.

## Development

```bash
python -m pip install -e './toolkit[dev]'
ruff check toolkit
ruff format --check toolkit
python -m unittest discover -s toolkit/tests -v
python -m build toolkit
```

Tests use temporary files and mocked HTTP/subprocess calls; no deployed server,
UniProt access, container engine or real `calNf` installation is required.
CI runs these checks on Python 3.12. Before committing, inspect `git diff`
(including renamed scripts) and keep unrelated Web/deployment changes separate.
