# MineProt Toolkit Manual

The toolkit prepares prediction outputs, uploads repository files and indexes
searchable metadata. This guide covers the standalone importer, ColabFold for
monomers, AlphaFold3 for complexes, the three batch commands, and MSA Neff
calculation. Plugins are documented separately below.

# Scripts

## Installation and server addresses

Use Python **3.12 or later**. Run examples from the MineProt project root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ./toolkit
mineprot-toolkit --help
```

Dependencies are declared in `toolkit/pyproject.toml`; there is no
`toolkit/scripts/requirements.txt`. Use `python -m pip install ./toolkit` for
a regular installation. The Python package and `toolkit/scripts/` entrypoints
accept the same arguments; append `--help` to inspect any command.

Networked commands default to the production management service at
**`http://127.0.0.1:8081`**. Run them on the deployment server or through a tunnel:

```bash
ssh -N -L 8081:127.0.0.1:8081 user@server
```

In development, explicitly use the writable Web address, for example port
8080. The meaning of `--url` depends on the command:

| Command | URL expected | Default |
| --- | --- | --- |
| `import_single.py` | Site base URL; entered interactively or saved as `url` | `http://127.0.0.1:8081` |
| `ai/colabfold/import.sh` | Site base URL | `http://127.0.0.1:8081` |
| `ai/colabfold/transform.py` | Full PDB-to-CIF endpoint | `http://127.0.0.1:8081/api/pdb2alphacif/` |
| `batch/import_es.py` | Elasticsearch proxy endpoint | `http://127.0.0.1:8081/api/es` |
| `batch/import_repo.py` | Repository import endpoint | `http://127.0.0.1:8081/api/import2repo/` |

AlphaFold3 transformation and Neff calculation run locally. `prepare_beacon.py`
uses external annotation services rather than a MineProt URL. See the
[deployment guide](Deployment-manual.md) for production/development modes and
[API manual](API-manual.md) for request formats.

## import_single.py

Import one PDB, CIF or mmCIF structure, optionally gzip-compressed, together
with optional confidence JSON and A3M files:

```bash
python toolkit/scripts/import_single.py
# Equivalent installed command:
mineprot-toolkit import-single
```

The interactive prompts collect the site URL, source files, storage format,
pLDDT calculation choice, protein name, repository and annotation. Source files
are never renamed or modified. Server files use the chosen protein name.
The importer uploads the files, then writes their Elasticsearch document; its
`seq` field is intentionally empty. File uploads and metadata writes are not
one transaction: inspect the output before retrying a failed import.

Storage choices are `plain`, `gz` and `fcz`. FCZ is lossy, accepts single-chain
protein structures, and uses Foldcomp 1.0.0; its JSON/A3M companions use gzip.
Use plain or gzip CIF for complexes. pLDDT calculation prefers confidence JSON,
then explicit ModelCIF pLDDT, then C-alpha B-factors; when calculation is disabled,
the score is `-1.0`. Treat B-factors as pLDDT only for suitable predictions.

You can save the interactive inputs as JSON and replay them:

```bash
python toolkit/scripts/import_single.py -i /path/to/import_single.json
# Replace conflicting content and metadata without prompting:
python toolkit/scripts/import_single.py -i /path/to/import_single.json -f
```

Example configuration for one predicted complex:

```json
{
  "version": 1,
  "url": "http://127.0.0.1:8081",
  "structure": "complex.cif",
  "compression": "gz",
  "json": "complex.json",
  "msa": null,
  "calculate_plddt": true,
  "name": "complex_ab",
  "repo": "complexes",
  "homolog": "",
  "database": "",
  "description": ["Protein A / protein B complex", "complex_ab"]
}
```

Relative source paths resolve from the configuration file's directory.
Interactive saves use absolute paths. Scores are recomputed on replay.
Without `-f`, different existing content or metadata prompts for confirmation;
storage-format conflicts still fail with `-f`.

## ai/colabfold: monomer example

### Transform results

For a directory containing monomer `result.zip` archives:

```bash
python toolkit/scripts/ai/colabfold/transform.py \
  -i /path/to/colabfold_results -o /path/to/monomers -z -n 0
```

`-i` is always a directory, including with `-z`; place ZIP files inside it.
Without `-z`, the script scans the directory's immediate result files. It selects
the rank-1 unrelaxed PDB by default and the matching score JSON and A3M when
present, then requests CIF conversion from MineProt. Add `-r` to select a relaxed
rank-1 PDB; that file must exist. A typical accepted result includes:

```text
test_a5e17.a3m
test_a5e17_unrelaxed_rank_001_alphafold2_ptm_model_3_seed_000.pdb
test_a5e17_scores_rank_001_alphafold2_ptm_model_3_seed_000.json
```

The selected files become `<name>.pdb`, `<name>.cif`, `<name>.json` and
`<name>.a3m` when companions are available. PNGs, logs and other model ranks
are not exported. PAE values in copied JSON are rounded to integers.

| Option | Meaning |
| --- | --- |
| `-i PATH`, `-o PATH` | Required input and output directories. |
| `-z` | Read ZIP archives inside the input directory. |
| `-r` | Select relaxed rather than unrelaxed structures. |
| `-n 0` | Preserve the filename prefix; default. |
| `-n 1` | Use the first A3M header's first word; requires A3M. |
| `-n 2` | Generate an `MP_...` name per prediction. |
| `-n 3` | Prompt for a name per prediction. |
| `-f` | Reprocess existing output files. |
| `--url URL` | Full conversion endpoint, for example `http://127.0.0.1:8080/api/pdb2alphacif/`. |

### Import monomers

Run the two batch commands after transformation:

```bash
python toolkit/scripts/batch/import_es.py -i /path/to/monomers -n monomers -a
python toolkit/scripts/batch/import_repo.py -i /path/to/monomers -n monomers
```

Or use the Bash pipeline to transform, index with `-a`, and upload in one run:

```bash
bash toolkit/scripts/ai/colabfold/import.sh /path/to/colabfold_results \
  --repo monomers --zip --name-mode 0 \
  --python "$(command -v python)" --url http://127.0.0.1:8081
```

Add `--relax` only if rank-1 relaxed models are available. The pipeline uses the
default upload mode (all supported files, plain storage). To choose gzip, FCZ,
overwrite behavior or batch sizes, run the stages separately. A failed stage
stops the pipeline. Its temporary data directory is removed on exit; the printed
log path remains for diagnosis. UniProt annotations depend on recognizable MSA
identifiers and successful external lookups; they are not guaranteed for every model.

## ai/alphafold3: complex example

### Transform results locally

The transformer accepts three input shapes:

```bash
# One ZIP, extracted temporarily and treated as one result directory.
python toolkit/scripts/ai/alphafold3/transform.py \
  -i /path/to/result.zip -o /path/to/complexes
# One result directory.
python toolkit/scripts/ai/alphafold3/transform.py \
  -i /path/to/complex_ab -o /path/to/complexes
# A directory containing immediate result subdirectories, processed one by one.
python toolkit/scripts/ai/alphafold3/transform.py \
  -i /path/to/af3_results -o /path/to/complexes
```

The script detects the layout from an `msas/` directory:

| Input layout | CIF source | JSON sources merged at the top level |
| --- | --- | --- |
| With `msas/` | `*_model_0.cif` | `*_full_data_0.json` + `*_summary_confidences_0.json` |
| Without `msas/` | `*_model.cif` | `*_confidences.json` + `*_summary_confidences.json` |

For example, `complex_ab_model_0.cif` produces `complex_ab.cif` and
`complex_ab.json`. CIF bytes are preserved. Both confidence files must contain
JSON objects; summary fields take precedence on duplicate keys. Confidence and
PAE token metadata are retained. `msas/` selects the layout but is not exported.
There is no `--url` parameter or conversion request.

ZIP input supports a single enclosing result directory, rather than a batch
of unrelated results. For parent-directory input, failures are reported per
subdirectory and processing continues, with a nonzero final exit status if any
failed. Complete existing output pairs are skipped unless `-f` is supplied;
partial pairs require `-f`, and duplicate prefixes across subdirectories fail.

Index and upload the prepared complexes using the same repository name:

```bash
python toolkit/scripts/batch/import_es.py -i /path/to/complexes -n complexes
python toolkit/scripts/batch/import_repo.py -i /path/to/complexes -n complexes -m 1 -z
```

Mode 1 includes CIF and JSON. This workflow keeps multichain CIFs intact and
does not require a PDB or A3M. JSON `atom_plddts` supplies the metadata score.
PAE uses `pae` and available token metadata. Salign automatically uses complex
alignment when either structure has multiple polymer chains; hinge is ignored.

### Additional AlphaFold3 preparation commands

These commands prepare or select predictions; they do not run AlphaFold3:

| Script under `toolkit/scripts/ai/alphafold3/` | Use |
| --- | --- |
| `prepare_complex.py` | Generate AF3 input JSON from whitespace-separated protein groups. |
| `prepare_pair.py` | Combine chain entries from matching `<name>/<name>_data.json` files across two or more input directories. |
| `select_max.py` | For matching result subdirectory names across runs, copy immediate files from the one with highest `iptm`. |

For example, given `groups.txt` containing `protein_a protein_b` on one line
and `proteins.fasta` containing both identifiers:

```bash
python toolkit/scripts/ai/alphafold3/prepare_complex.py \
  --list /path/to/groups.txt --fasta /path/to/proteins.fasta \
  -o /path/to/af3_inputs -n 5 -t 2
```

The generated name is `protein_a_x_protein_b`, with chain IDs A/B, five random
seeds, dialect `alphafold3` and version 2. `--a3m DIR [DIR ...]` can supply MSA
paths; the first matching A3M provides the sequence, with FASTA as fallback.
Among `--fasta` paths only the first existing file is loaded. Inspect generated
sequences before prediction: missing identifiers can produce empty sequences.
MSA paths must be accessible in the AlphaFold3 runtime.

`prepare_pair.py -i RUN_A RUN_B -o OUTPUT` mixes chain-position entries and
excludes combinations taken entirely from one input. `select_max.py -i RUN_A
RUN_B -o OUTPUT` currently recognizes only `*_summary_confidences.json` and
copies files, not nested directories. It does not select the
`*_summary_confidences_0.json` layout; use `transform.py` directly for that layout.

## batch/import_es.py

Create Elasticsearch metadata through MineProt's API; this does not upload
repository files. Input is a local directory, not a MineProt URL:

```bash
python toolkit/scripts/batch/import_es.py -i /path/to/models -n demo -t 4
```

| Option | Default | Meaning |
| --- | --- | --- |
| `-i PATH` | Required | Scan immediate structure files. |
| `-n NAME` | Input directory name | Target Elasticsearch index; match the repository name. |
| `-a` | Off | Attempt UniProt/GO/InterPro annotation using companion A3M identifiers. |
| `-t N` | `1` | Worker threads. |
| `--max-msa N` | `10` | Maximum MSA identifiers considered for annotation. |
| `-f` | Off | **Delete the entire target index before importing.** |
| `--url URL` | Local management `/api/es` | Full Elasticsearch proxy endpoint. |

PDB, CIF/mmCIF and FCZ are supported, including gzip PDB/CIF. Companion JSON
and A3M may also use gzip. For each name, the script chooses CIF, then PDB,
then FCZ, preferring plain over gzip within each extension. Existing document
IDs are skipped unless the index was reset with `-f`.

The sequence joins amino-acid residues from all chains in the first model.
Scores prefer companion JSON pLDDT (including AF3 `atom_plddts`), then explicit
ModelCIF pLDDT, then C-alpha B-factors, with a heavy-atom mean when C-alpha is
missing. A repo containing only CIF or FCZ can therefore be indexed without
JSON or A3M. With `-a`, missing A3M skips annotation and keeps the model name as
a keyword. Invalid structures or scores fail rather than silently creating
placeholder documents. FCZ decoding runs locally in a separate process.

## batch/import_repo.py

Upload repository files through batch preflight and multipart binary requests.
Use `import_es.py` separately for searchable metadata:

```bash
python toolkit/scripts/batch/import_repo.py -i /path/to/models -n demo -m 0 -z
```

| Option | Default | Meaning |
| --- | --- | --- |
| `-i PATH` | Required | Scan immediate files in a local directory. |
| `-n NAME` | Input directory name | Target repository. |
| `-m MODE` | `0` | File selection/storage mode below. |
| `-z` | Off | Gzip storage for ordinary files; incompatible with mode 4. |
| `-f` | Off | Replace different content in the same storage format. |
| `--batch-files N` | `256` | Files per batch, 1–256. |
| `--batch-mib M` | `16` | Target request size in MiB, greater than 0 and at most 64. |
| `--workers N` | `2` | Concurrent batches, 1–8. |
| `--url URL` | Local management `/api/import2repo/` | Full import endpoint. |

| Mode | Selected local files | Storage |
| --- | --- | --- |
| `0` | `.a3m`, `.cif`, `.json`, `.pdb` | Plain, or gzip with `-z`. |
| `1` | `.cif`, `.json`, `.pdb` | Plain, or gzip with `-z`. |
| `2` | `.json`, `.pdb` | Plain, or gzip with `-z`. |
| `3` | `.pdb` | Plain, or gzip with `-z`. |
| `4` | `.pdb` | Compress locally to same-stem FCZ with Foldcomp 1.0.0. |

Extensions are case-sensitive. These modes do not select existing local `.gz`,
`.mmcif` or `.fcz` files. CIF-only repositories use mode 0 or 1. Mode 4 requires
single-chain PDBs, does not upload companions, and has no multichain fallback.
Local source files are never rewritten. Keep originals when exact coordinates
matter because FCZ is lossy.

```bash
# Gzip PDB and JSON storage.
python toolkit/scripts/batch/import_repo.py -i /path/to/monomers -n monomers -m 2 -z
# Compress single-chain PDBs directly to server FCZ files.
python toolkit/scripts/batch/import_repo.py -i /path/to/monomers -n monomers -m 4
```

The client checks a manifest, uploads eligible files, verifies hashes, reuses
connections and retries transient failures. Identical content is skipped even
with `-f`. Different same-format content is skipped without `-f`, replaced
with it. Plain/gzip/FCZ mismatches, multiple PDB/FCZ variants and `.fcz.gz`
conflicts are errors even with `-f`; changing format requires a separate
migration. Transport gzip is independent of gzip storage.

One failed file does not roll back successful files. Inspect per-file results;
the command exits nonzero on failures. A server without the batch API is
reported as unsupported. See the [batch API reference](API-manual.md#6-batch-repository-imports)
for checksums, limits and response statuses.

## batch/prepare_beacon.py

Prepare PDB copies and metadata for a 3D-Beacons client:

```bash
python toolkit/scripts/batch/prepare_beacon.py \
  -i /path/to/preprocessed_monomers -o /path/to/beacons/data -t 2 --max-msa 50
```

`-i` and `-o` are required; `-t` defaults to 1 and `--max-msa` to 50. This
command scans immediate **uncompressed `.pdb` files**, requires matching
`.json` with a numeric `plddt` list and matching `.a3m`, and calls annotation
services to find a suitable mapping accession. The A3M must have the query
sequence on line 3 and homolog records from line 4, as in toolkit-prepared
monomer alignments. Arbitrary A3M layouts may need adaptation first.

It creates `pdb/`, `cif/`, `metadata/` and `index/` under the output directory,
copies successful PDBs into `pdb/` and writes mapping/confidence JSON into
`metadata/`. It does not populate CIF or build the downstream index. Missing
companions or mappings fail per model; any failure gives a nonzero exit status.
This command does not accept a CIF-only or FCZ-only repository directly.

## misc/calculate_neff.py

**Neff is the effective number of sequences in an MSA**, a measure of sequence
diversity after accounting for redundancy. More similar sequences contribute
less independent information; it is not just the number of FASTA records or
a model confidence score. A common weighting sums the inverse number of
neighbors above a sequence-identity threshold; normalization conventions vary.
See the [NEFFy methods paper](https://doi.org/10.1093/bioinformatics/btaf222).
A larger Neff generally indicates a more diverse MSA, without guaranteeing
prediction accuracy for a particular target.

The script converts A3M to alignment text and invokes an external **`calNf`**
executable. It does not implement a separate Neff estimator. Install `calNf`
separately and put it on PATH or pass its full path:

```bash
python toolkit/scripts/misc/calculate_neff.py \
  --a3m /path/to/msas --cal-nf /path/to/calNf -t 4 -s 0.8 > neff.tsv
# Equivalent installed command:
mineprot-toolkit misc calculate-neff --a3m /path/to/msas --cal-nf /path/to/calNf
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--a3m DIR` | Required | Scan immediate `.a3m`, `.a3m.gz`, `.a3m.xz` and `.a3m.bz2` files. |
| `--cal-nf PATH` | `calNf` | External executable; `--calNf` is retained as an alias. |
| `-t N` | `1` | Worker threads; must be positive. |
| `-s VALUE` | `0.8` | Similarity parameter passed to `calNf`. |
| `--norm N` | `0` | Normalization argument passed to `calNf`. |
| `--max N` | `0` | Maximum argument passed to `calNf`. |
| `--nonre N` | Omitted | Optional final argument passed to `calNf`. |

For each file, the script drops header/comment lines and lowercase insertion
characters, writes a temporary `.aln`, and runs:

```text
calNf ALIGNMENT S NORM MAX [NONRE]
```

The numeric conventions of `--norm`, `--max` and `--nonre` depend on the
installed executable; MineProt passes them through and returns its stripped
stdout. Output is tab-separated `alignment_name<TAB>result`, with no header
and completion-dependent order. For compressed input, the compression suffix
is removed but `.a3m` remains in the printed name. Failures produce `Error:`
rows and a nonzero exit status. Temporary alignments are cleaned up. Neither
the script nor its output is imported into MineProt automatically.


# Plugins

The JavaScript plugins connect MineProt with sequence and structure search
services. Choose either a browser userscript installation or a server-side
embedded installation for each integration; loading both duplicates its buttons.

| Plugin | Page where it runs | Purpose |
| --- | --- | --- |
| `sequenceserver.js` | SequenceServer results | Link BLAST hits to MineProt search. |
| `alphafill.js` | MineProt search | Upload the displayed structure as CIF to AlphaFill. |
| `foldseek2mineprot.js` | Foldseek-App results | Link Foldseek hits to MineProt search. |
| `mineprot2foldseek.js` | MineProt search | Upload the displayed structure as PDB to Foldseek. |

The scripts are in `toolkit/plugins/`. MineProt still serves `/search.php` as a
browser URL, but its current page template is **`web/templates/search.html`**.
Do not edit a former `web/search.php` file to customize the Python service.

## Browser userscripts: common setup

1. Install [Tampermonkey](https://www.tampermonkey.net/) in the browser.
2. Copy the appropriate file from `toolkit/plugins/` into a new userscript.
3. Replace its `// @include` placeholder with the URL pattern of the page where
   it runs, including any nondefault port. For example:

   ```javascript
   // @include *://localhost:8080/search.php*
   ```

4. Set the destination service URL in the script's startup function where
   required, then save and enable the userscript.

Userscript URL metadata affects Tampermonkey only. It does not restrict a
script loaded through a normal HTML `<script src="...">` tag, so embed plugins
only on the pages where they are needed.

## Embed plugins in MineProt search

This installation method applies to **AlphaFill** and **MineProt to Foldseek**.
The Python service exposes `web/assets/` at `/assets/`; `toolkit/plugins/` is
not served as a Web directory and is not copied into the Web image.

From the project root, copy the desired scripts into the static assets:

```bash
mkdir -p web/assets/js/plugins
cp toolkit/plugins/alphafill.js web/assets/js/plugins/alphafill.js
cp toolkit/plugins/mineprot2foldseek.js web/assets/js/plugins/mineprot2foldseek.js
```

Edit the copied scripts to select the target services. Their startup calls are:

```javascript
// In alphafill.js:
MineProt2AlphaFill("https://alphafill.eu");

// In mineprot2foldseek.js:
MineProt2Foldseek("https://search.foldseek.com");
```

In **`web/templates/search.html`**, add the following immediately before
`</body>`, after the search cards and existing page scripts:

```html
{% if Search_Result_Num %}
<script src="/assets/js/plugins/alphafill.js"></script>
<script src="/assets/js/plugins/mineprot2foldseek.js"></script>
{% endif %}
```

Include only the plugins you want. Load each script once per page, not inside
`search_card.html` or a result loop. The files already contain startup calls;
do not call their entry functions again. The conditional avoids starting their
DOM polling on an empty search page. Do not add `type="module"` to these tags;
the existing scripts use ordinary global functions.

The plugins locate `name="search_result_link"` elements generated by
`web/templates/search_card.html`. Each element's ID is the extension-free API
path `/api/file/<repo>/<protein>`. The plugins append `.cif` or `.pdb`, allowing
the server to supply converted structures even when only FCZ is stored. Keep
these hooks if you customize the search-card markup.

The current Compose configuration bind-mounts `./web` into the Web container,
so the host's copied assets and edited template are visible there. The template
loader normally reloads changed templates; if the server has disabled template
reloading, restart the Web service. Rebuild before deploying an updated image
without that source mount. Refresh the browser to reload modified JavaScript.

### AlphaFill

The plugin downloads the search hit's CIF through MineProt and uploads it to
the configured AlphaFill service, then opens the returned model page. Use
`alphafill.js` with either the userscript setup or the embedded setup above.
To use another compatible AlphaFill deployment, change the URL passed to
`MineProt2AlphaFill()` in the copy you actually load.

### MineProt to Foldseek

The plugin downloads the hit's PDB through MineProt, submits it to the
configured Foldseek service, and opens the result page. Use
`mineprot2foldseek.js` with either installation method above. Change the URL
passed to `MineProt2Foldseek()` for another compatible deployment. Its database
selection is configured in `AddSeek()`; check those identifiers against your
target Foldseek installation. Cross-origin uploads require the destination
service to accept the browser request.

## SequenceServer to MineProt

`sequenceserver.js` adds a MineProt search link to each compatible SequenceServer
hit. The sequence identifiers in the BLAST database must match searchable
protein names in MineProt. To distinguish repositories, append a repository
suffix such as `protein_001|repo=demo` to the identifier and include the protein
name in its indexed annotation strings.

The older `msa2seq.sh` reference does not correspond to a script in this
checkout. Prepare the amino-acid FASTA for your BLAST database separately;
`fsdb2seq.sh` exports Foldseek 3Di sequences and is not an amino-acid FASTA
replacement for BLAST.

### Tampermonkey

Set the SequenceServer page pattern in `// @include`, for example:

```javascript
// @include *://localhost:4567/*
```

Replace the existing startup call with your MineProt base URL, without a
trailing slash:

```javascript
(function () {
    MainFunction("https://mineprot.example.org", 0);
})();
```

### Embedded in SequenceServer

1. Configure the MineProt URL in a copy of `sequenceserver.js`.
2. Serve that copy from SequenceServer's own public/static assets and load it
   once from the results-page template or its layout, after the result markup.
   In versions using `views/report.erb`, that file is the legacy insertion
   point; other releases may use a different results entry or shared layout.
3. For example, if your asset is served at `/mineprot/sequenceserver.js`, add:

   ```html
   <script src="/mineprot/sequenceserver.js"></script>
   ```

4. Restart or rebuild the SequenceServer deployment as required, then verify
   that its result markup contains `.overview` and `div.hit-links`, which this
   plugin expects.

This script belongs to SequenceServer, not MineProt's search template. Its
static asset URL and template location depend on the SequenceServer version
and deployment; `/mineprot/` above is an example to configure, not a route
provided by MineProt.

## Foldseek to MineProt

`foldseek2mineprot.js` changes compatible Foldseek-App hit links to open
MineProt search. The Foldseek database label must match the MineProt repository
name. Protein names are derived from the hit titles after removing recognized
structure-file suffixes; ensure the same names are searchable in MineProt.

### Tampermonkey

Set the Foldseek-App page pattern:

```javascript
// @include *://localhost:8877/*
```

Replace the existing startup call with your MineProt base URL:

```javascript
(function () {
    MainFunction("https://mineprot.example.org", 0);
})();
```

### Embedded in Foldseek-App

1. Configure the MineProt URL in a copy of `foldseek2mineprot.js`.
2. Add the script to the Foldseek-App frontend build, or serve it from that
   frontend's public/static directory and reference its deployed URL from the
   HTML entry. In source layouts using `frontend/index.html`, place the script
   after the application mount element. Preserve the existing bundler template
   expressions. See the [upstream HTML entry](https://github.com/soedinglab/MMseqs2-App/blob/master/frontend/index.html).
3. For example, **after arranging for the frontend to serve this path**, load:

   ```html
   <script src="/mineprot/foldseek2mineprot.js"></script>
   ```

4. Rebuild and redeploy the Foldseek frontend image. Confirm that the installed
   release's hit markup matches the selectors in the plugin, including the
   `v-table result-table` element and database-label layout.

This script runs in Foldseek-App, not MineProt. Changing only MineProt's
`web/templates/search.html` will not alter external Foldseek result links.
Both external-result plugins depend on their host application's HTML structure;
verify the links after upgrading SequenceServer or Foldseek-App.
