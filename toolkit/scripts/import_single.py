#!/usr/bin/env python3
"""Interactive single-model repository + Elasticsearch import.

Run: python toolkit/scripts/import_single.py
Replay: python toolkit/scripts/import_single.py -i import_single.json
Overwrite without prompts: python toolkit/scripts/import_single.py -i import_single.json -f
Optional JSON/MSA files are renamed on the server, never on the local disk.

Saved configuration fields:
    version: 1
    url: site URL without /api
    structure: source PDB/CIF path
    compression: plain, gz, or fcz (FCZ companions always use gzip)
    json, msa: optional source paths, or null
    calculate_plddt: boolean; prefer JSON confidence values over the structure
    name, repo, homolog, database: strings
    description: array of strings
Relative source paths are resolved from the configuration file's directory.
Interactive runs save absolute paths. Calculated scores are recomputed on replay.
"""
import argparse
import base64
import gzip
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
from urllib.parse import quote, urlsplit, urlunsplit

import requests

from import2repo import request as batch_request, results_by_name, session, upload_batch


STRUCTURE_SUFFIXES = {'.pdb', '.cif', '.mmcif'}


def ask_choice(prompt, choices, default):
    while True:
        answer = input(prompt).strip().lower() or default
        if answer in choices:
            return choices[answer]
        print('Invalid input. Please select one of the listed options.')


def ask_yes(prompt):
    return ask_choice(prompt, {'y': True, 'yes': True, '1': True,
                              'n': False, 'no': False, '2': False}, 'n')


def normalize_url(raw):
    raw = raw.strip()
    if '://' not in raw:
        raw = 'http://' + raw
    parts = urlsplit(raw)
    if (parts.scheme not in ('http', 'https') or not parts.hostname or parts.query
            or parts.fragment or parts.username or parts.password):
        raise ValueError('Enter an HTTP(S) site URL without /api, query parameters, or credentials')
    parts.port  # Validate a supplied port before issuing any requests.
    path = parts.path.rstrip('/')
    if re.search(r'/api(?:/|$)', path):
        raise ValueError('Use the site URL without an /api suffix')
    return urlunsplit((parts.scheme, parts.netloc, path, '', ''))


def ask_url():
    while True:
        raw = input('Site URL (no /api suffix) [http://127.0.0.1]: ').strip() or 'http://127.0.0.1'
        try:
            return normalize_url(raw)
        except ValueError as exc:
            print(exc)


def logical_path(path):
    return path.with_suffix('') if path.suffix.lower() == '.gz' else path


def ask_path(prompt, optional=False, structure=False):
    while True:
        raw = input(prompt).strip()
        if not raw and optional:
            return None
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'"):
            raw = raw[1:-1]
        path = Path(os.path.expandvars(raw)).expanduser()
        if not raw or not path.is_file():
            print('File not found. Enter an absolute or relative local file path.')
            continue
        if structure and logical_path(path).suffix.lower() not in STRUCTURE_SUFFIXES:
            print('Supported structure formats: PDB, CIF, mmCIF, including .gz files.')
            continue
        return path.resolve()


def component(name):
    if not name or name in ('.', '..') or any(c in '/\\' or ord(c) < 32 or ord(c) == 127 for c in name):
        raise ValueError('Names must not be empty or contain path separators or control characters')
    return name


def ask_name(default):
    while True:
        name = input(f'Name without extension [{default}]: ').strip() or default
        try:
            return component(name)
        except ValueError as exc:
            print(exc)


def validate_repo(repo):
    component(repo)
    if (repo.lower() != repo or repo[0] in '-_+' or len(repo.encode()) > 255
            or any(c.isspace() or c in '\\/*?"<>|,#:' for c in repo)):
        raise ValueError('Repository names must be lowercase, must not start with -/_/+, '
                         'and must not contain spaces or ES-reserved characters')
    return repo


def ask_repo(default):
    while True:
        repo = input(f'Repository / ES index [{default}]: ').strip() or default
        try:
            return validate_repo(repo)
        except ValueError as exc:
            print(exc)


def ask_descriptions(name, homolog):
    print('Descriptions: separate entries with semicolons or newlines. Enter a blank line to finish.')
    result = []
    while True:
        line = input('> ')
        if not line.strip():
            break
        for item in re.split(r'[;\uFF1B]', line):
            item = item.strip()
            if item and item not in result:
                result.append(item)
    for identifier in (name, homolog):
        if identifier and identifier not in result:
            result.append(identifier)
    return result


def read_bytes(path):
    data = path.read_bytes()
    return gzip.decompress(data) if path.suffix.lower() == '.gz' else data


def parse_structure(data, suffix):
    try:
        import gemmi
    except ImportError as exc:
        raise RuntimeError('Gemmi is required: pip install gemmi==0.7.1') from exc
    text = data.decode('utf-8-sig')
    block = None
    if suffix == '.pdb':
        structure = gemmi.read_pdb_string(text)
    else:
        block = gemmi.cif.read_string(text).sole_block()
        structure = gemmi.make_structure_from_block(block)
    if not len(structure) or not any(len(residue) for chain in structure[0] for residue in chain):
        raise ValueError('No atomic coordinates were found in the structure')
    return structure, block


def protein_residues(structure):
    import gemmi
    return [residue for chain in structure[0] for residue in chain
            if len(residue) and gemmi.find_tabulated_residue(residue.name).is_amino_acid()]


def calculate_score(structure, block):
    """Use explicit ModelCIF pLDDT, else one C-alpha B-factor per residue."""
    residues = protein_residues(structure)
    if not residues:
        raise ValueError('No amino-acid residues are available for pLDDT calculation')
    if block is not None:
        metrics = block.get_mmcif_category('_ma_qa_metric.')
        local = block.get_mmcif_category('_ma_qa_metric_local.')
        metric_id = None
        for i, identifier in enumerate(metrics.get('id', [])):
            name = str(metrics.get('name', [''] * len(metrics['id']))[i]).lower()
            kind = str(metrics.get('type', [''] * len(metrics['id']))[i]).lower()
            mode = str(metrics.get('mode', ['local'] * len(metrics['id']))[i]).lower()
            if mode == 'local' and ('plddt' in name or kind == 'plddt'):
                metric_id = identifier
                break
        if metric_id is not None:
            if not all(key in local for key in ('metric_id', 'label_asym_id', 'label_seq_id', 'metric_value')):
                raise ValueError('CIF declares per-residue pLDDT but its metric data is incomplete')
            values = {}
            model_id = str(structure[0].num)
            for i, identifier in enumerate(local.get('metric_id', [])):
                if identifier != metric_id:
                    continue
                models = local.get('model_id')
                if models and str(models[i]) != model_id:
                    continue
                key = (str(local['label_asym_id'][i]), int(local['label_seq_id'][i]))
                value = float(local['metric_value'][i])
                if key in values and values[key] != value:
                    raise ValueError('CIF contains conflicting per-residue pLDDT values')
                values[key] = value
            try:
                scores = [values[(residue.subchain, residue.label_seq)] for residue in residues]
            except KeyError as exc:
                raise ValueError('Explicit CIF pLDDT metrics do not cover all protein residues') from exc
            source = 'CIF ModelCIF pLDDT (mean per residue)'
        else:
            scores = None
    else:
        scores = None
    if scores is None:
        scores = []
        for residue in residues:
            atoms = [atom for atom in residue if atom.element.name not in ('H', 'D', 'T')]
            ca = next((atom for atom in atoms if atom.name == 'CA'), None)
            if not atoms:
                raise ValueError('A protein residue has no readable heavy-atom B-factors')
            scores.append(float(ca.b_iso) if ca is not None else math.fsum(atom.b_iso for atom in atoms) / len(atoms))
        source = 'C-alpha B-factor (mean per residue; heavy-atom mean if C-alpha is absent)'
    if not scores or any(not math.isfinite(value) or not 0 <= value <= 100 for value in scores):
        raise ValueError('pLDDT must contain finite values in [0, 100]; check the input or disable calculation')
    return math.fsum(scores) / len(scores), source


def compress_fcz(name, structure):
    import gemmi
    try:
        if importlib.metadata.version('foldcomp') != '1.0.0':
            raise RuntimeError('FCZ mode requires foldcomp==1.0.0')
        import foldcomp
    except (ImportError, importlib.metadata.PackageNotFoundError) as exc:
        raise RuntimeError('FCZ mode requires: pip install foldcomp==1.0.0') from exc
    if len(structure) != 1:
        raise ValueError('FCZ supports only single-model, single-chain proteins; use plain or gz instead')
    chains = [chain for chain in structure[0] if len(chain)]
    if (len(chains) != 1 or any(not gemmi.find_tabulated_residue(residue.name).is_amino_acid()
                                for residue in chains[0])):
        raise ValueError('FCZ cannot preserve multiple chains, nucleic acids, water, or ligands; use plain or gz instead')
    if len(chains[0].name) > 1:
        structure = structure.clone()
        next(chain for chain in structure[0] if len(chain)).name = 'A'
    pdb = structure.make_pdb_string()
    data = foldcomp.compress(name, pdb)
    decoded = foldcomp.decompress(data)[1].encode('utf-8')
    return data, hashlib.sha256(decoded).hexdigest()


def file_item(name, data, storage='plain', content_sha256=None):
    item = {'name': name, 'storage': storage, 'size': len(data),
            'sha256': hashlib.sha256(data).hexdigest(),
            'encoding': 'identity' if storage == 'fcz' else 'gzip'}
    if content_sha256 is not None:
        item['content_sha256'] = content_sha256
    return item, data if storage == 'fcz' else gzip.compress(data, mtime=0)


def get_es(base_url, repo, document_id):
    response = session().get(f'{base_url}/api/es/{quote(repo, safe="")}/get/{quote(document_id, safe="")}',
                             timeout=(10, 60))
    if response.status_code == 404:
        return None
    response.raise_for_status()
    body = response.json()
    if body.get('found') is False:
        return None
    if body.get('found') is not True or not isinstance(body.get('_source'), dict):
        raise RuntimeError('Unexpected ES lookup response: ' + response.text[:300])
    return body['_source']


def run_import(base_url, repo, document, batch, force=False):
    endpoint = base_url + '/api/import2repo'
    body = {'repo': repo, 'force': force, 'files': [item for item, _ in batch]}
    checked = batch_request(endpoint + '/batch/check', json=body)
    names = [item['name'] for item, _ in batch]
    statuses = results_by_name(checked, names)
    for result in statuses.values():
        if result['status'] == 'error':
            raise RuntimeError(f"File preflight failed: {result['name']}: {result.get('error', '')}")
        if result['status'] not in ('upload', 'unchanged', 'exists'):
            raise RuntimeError('Unknown file preflight status: ' + str(result['status']))
    document_id = base64.b64encode(document['name'].encode('utf-8')).decode('ascii')
    previous = get_es(base_url, repo, document_id)
    conflicts = [name for name, result in statuses.items() if result['status'] == 'exists']
    metadata_changes = previous is not None and previous != document
    if not force and (conflicts or metadata_changes):
        if conflicts:
            print('Different file contents already exist on the server: ' + ', '.join(conflicts))
        if metadata_changes:
            print('An ES document with this name already exists with different metadata.')
        if not ask_yes('Overwrite the conflicting files / ES metadata? [y/N]: '):
            raise RuntimeError('Cancelled; no files or ES metadata were changed')
        force = True
    options = SimpleNamespace(n=repo, f=force, url=endpoint)
    print('\nImporting files...')
    results = upload_batch(options, batch)
    received = results_by_name({'results': results}, names)
    failures = []
    for name, result in received.items():
        print(f"  {repo}/{name}: {result['status']}" + (f" — {result.get('error', '')}" if result['status'] == 'error' else ''))
        if result['status'] not in ('imported', 'unchanged'):
            failures.append(name)
    if failures:
        raise RuntimeError('Some files were not imported; ES metadata was not written. Successfully uploaded files remain on the server. Fix the issue and rerun.')
    # Recheck metadata to avoid silently replacing a document created during upload.
    current = get_es(base_url, repo, document_id)
    if not force and current not in (None, previous, document):
        raise RuntimeError('ES metadata changed during upload and was not overwritten. Files were uploaded; inspect the server before rerunning.')
    response = session().post(f'{base_url}/api/es/{quote(repo, safe="")}/add/{quote(document_id, safe="")}',
                              json=document, timeout=(10, 60))
    response.raise_for_status()
    print(f'Import complete: {repo}/{document["name"]} (seq is empty)')


PLDDT_KEYS = ('plddt', 'plddts', 'residueplddt', 'residueplddts',
              'atomplddts', 'atomplddt', 'predictedlddt', 'meanplddt')


def json_score(payload):
    """Find named confidence fields, including nested AF2/AF3 JSON objects."""
    candidates = []
    pending = [(payload, '$')]
    while pending:
        node, path = pending.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                normalized = re.sub(r'[\s_-]', '', key).lower()
                location = f'{path}.{key}'
                if normalized in PLDDT_KEYS:
                    candidates.append((PLDDT_KEYS.index(normalized), location, value))
                elif normalized not in ('pae', 'predictedalignederror', 'distogram'):
                    if isinstance(value, (dict, list)):
                        pending.append((value, location))
        elif isinstance(node, list):
            pending.extend((node[i], f'{path}[{i}]') for i in range(len(node) - 1, -1, -1)
                           if isinstance(node[i], (dict, list)))
    # Prefer per-residue pLDDT, then per-atom values, then a supplied mean.
    for _, location, field in sorted(candidates, key=lambda item: item[0]):
        if field is None or field == []:
            continue
        values = []
        pending_values = [field]
        while pending_values:
            value = pending_values.pop()
            if isinstance(value, list):
                pending_values.extend(value)
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                value = float(value)
                if not math.isfinite(value) or not 0 <= value <= 100:
                    raise ValueError(f'{location} contains pLDDT outside the finite range [0, 100]')
                values.append(value)
            else:
                raise ValueError(f'{location} must be a number or an array of pLDDT numbers')
        if values:
            return math.fsum(values) / len(values), f'JSON {location} (mean of {len(values)} values)'
    return None


def interactive_config():
    print('MineProt single-model import (local source files are never renamed or modified)\n')
    url = ask_url()
    structure = ask_path('Structure path (PDB / CIF, optionally .gz): ', structure=True)
    compression = ask_choice('Compression: 1 plain / 2 gz / 3 fcz [1]: ',
                             {'1': 'plain', 'plain': 'plain', 'none': 'plain',
                              '2': 'gz', 'gz': 'gz', 'gzip': 'gz', '3': 'fcz', 'fcz': 'fcz'}, '1')
    json_path = ask_path('JSON path (blank to skip): ', optional=True)
    msa_path = ask_path('MSA path (blank to skip; stored as .a3m): ', optional=True)
    score_enabled = ask_yes('Calculate pLDDT (JSON first, then structure)? [y/N]: ')
    name = ask_name(logical_path(structure).stem)
    homolog = input('Homolog (blank for none): ').strip()
    database = ask_choice('Database: 1 afdb / 2 uniprotkb / 3 uniparc / 4 none [4]: ',
                          {'1': 'afdb', 'afdb': 'afdb', '2': 'uniprotkb', 'uniprotkb': 'uniprotkb',
                           '3': 'uniparc', 'uniparc': 'uniparc', '4': '', 'none': ''}, '4')
    descriptions = ask_descriptions(name, homolog)
    repo = ask_repo(structure.parent.name.lower())
    return {'version': 1, 'url': url, 'structure': str(structure), 'compression': compression,
            'json': str(json_path) if json_path else None, 'msa': str(msa_path) if msa_path else None,
            'calculate_plddt': score_enabled, 'name': name, 'homolog': homolog,
            'database': database, 'description': descriptions, 'repo': repo}


def validate_config(config, directory):
    """Resolve relative source paths against the configuration file's directory."""
    if not isinstance(config, dict):
        raise ValueError('Import configuration must be a JSON object')
    allowed = {'version', 'url', 'structure', 'compression', 'json', 'msa', 'calculate_plddt',
               'name', 'homolog', 'database', 'description', 'repo'}
    unknown = set(config) - allowed
    if unknown:
        raise ValueError('Unknown configuration fields: ' + ', '.join(sorted(unknown)))
    result = dict(config)
    if type(result.get('version', 1)) is not int or result.get('version', 1) != 1:
        raise ValueError('Unsupported import configuration version')
    for key in ('url', 'structure', 'repo'):
        if not isinstance(result.get(key), str) or not result[key].strip():
            raise ValueError(f'Configuration field {key!r} must be a non-empty string')
    result['version'] = 1
    result['url'] = normalize_url(result['url'])
    result['repo'] = validate_repo(result['repo'].strip())
    for key in ('structure', 'json', 'msa'):
        value = result.get(key)
        if key != 'structure' and (value is None or value == ''):
            result[key] = None
            continue
        if not isinstance(value, str):
            raise ValueError(f'Configuration field {key!r} must be a file path or null')
        path = Path(os.path.expandvars(value)).expanduser()
        if not path.is_absolute():
            path = directory / path
        if not path.is_file():
            raise ValueError(f'{key} file not found: {path}')
        result[key] = str(path.resolve())
    source = logical_path(Path(result['structure']))
    if source.suffix.lower() not in STRUCTURE_SUFFIXES:
        raise ValueError('Structure must be PDB, CIF or mmCIF, optionally gzip-compressed')
    for key, default in (('name', source.stem), ('homolog', ''), ('database', '')):
        value = result.get(key, default)
        if not isinstance(value, str):
            raise ValueError(f'Configuration field {key!r} must be a string')
        result[key] = value.strip()
    result['name'] = component(result['name'] or source.stem)
    if result['database'] not in ('', 'afdb', 'uniprotkb', 'uniparc'):
        raise ValueError('database must be afdb, uniprotkb, uniparc, or an empty string')
    compression = result.get('compression', 'plain')
    if not isinstance(compression, str) or compression not in ('plain', 'none', 'gz', 'gzip', 'fcz'):
        raise ValueError('compression must be plain, gz, or fcz')
    result['compression'] = {'none': 'plain', 'gzip': 'gz'}.get(compression, compression)
    if type(result.get('calculate_plddt', False)) is not bool:
        raise ValueError('calculate_plddt must be true or false')
    result.setdefault('calculate_plddt', False)
    description = result.get('description', [])
    if isinstance(description, str):
        description = re.split(r'[;\uFF1B\r\n]', description)
    if not isinstance(description, list) or any(not isinstance(item, str) for item in description):
        raise ValueError('description must be an array of strings or semicolon/newline-separated text')
    result['description'] = []
    for item in description + [result['name'], result['homolog']]:
        item = item.strip()
        if item and item not in result['description']:
            result['description'].append(item)
    return result


def execute_config(config, force=False):
    source_path = logical_path(Path(config['structure']))
    raw = read_bytes(Path(config['structure']))
    structure, block = parse_structure(raw, source_path.suffix.lower())
    json_data, json_payload = None, None
    if config['json']:
        json_data = read_bytes(Path(config['json']))
        json_payload = json.loads(json_data.decode('utf-8-sig'))
    score, score_source = -1.0, 'calculation disabled'
    if config['calculate_plddt']:
        extracted = json_score(json_payload) if json_payload is not None else None
        if extracted is None:
            if json_data is not None:
                print('No pLDDT values found in JSON; calculating from the structure.')
            extracted = calculate_score(structure, block)
        score, score_source = extracted
    name = config['name']
    document = {'name': name, 'seq': '', 'score': score,
                'anno': {'homolog': config['homolog'], 'database': config['database'],
                         'description': config['description']}}
    # FCZ applies only to the structure; all companion files use gzip storage.
    storage = 'gzip' if config['compression'] in ('gz', 'fcz') else 'plain'
    if config['compression'] == 'fcz':
        print('FCZ is lossy. JSON/MSA use gzip; pLDDT is calculated before FCZ compression.')
        compressed, digest = compress_fcz(name, structure)
        batch = [file_item(name + '.fcz', compressed, 'fcz', digest)]
    else:
        suffix = '.pdb' if source_path.suffix.lower() == '.pdb' else '.cif'
        batch = [file_item(name + suffix, raw, storage)]
    if json_data is not None:
        batch.append(file_item(name + '.json', json_data, storage))
    if config['msa']:
        batch.append(file_item(name + '.a3m', read_bytes(Path(config['msa'])), storage))
    print(f"\nTarget: {config['url']} / {config['repo']}")
    print('Files: ' + ', '.join(item['name'] + ('.gz' if item['storage'] == 'gzip' else '') for item, _ in batch))
    print(f'Score: {score:.6f} ({score_source})')
    print('Annotation: ' + json.dumps(document['anno'], ensure_ascii=False))
    try:
        run_import(config['url'], config['repo'], document, batch, force=force)
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        raise RuntimeError(f'Import did not complete: {exc}. File uploads and ES writes are not '
                           'one transaction; inspect the output before rerunning.') from exc


def save_config(config):
    try:
        raw = input('\nSave these inputs as JSON? Enter a path (folder ending in / uses import_single.json; blank skips): ').strip()
    except EOFError:
        print('\nConfiguration not saved.')
        return
    if not raw:
        return
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'"):
        raw = raw[1:-1]
    target = Path(os.path.expandvars(raw)).expanduser()
    if raw.endswith('/') or target.is_dir():
        target = target / 'import_single.json'
    target = target.resolve()
    if any(config[key] and target == Path(config[key]).resolve() for key in ('structure', 'json', 'msa')):
        raise ValueError('The configuration path must not overwrite a source structure, JSON, or MSA file')
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent,
                                         prefix='.import_single-', suffix='.tmp', delete=False) as output:
            temporary = Path(output.name)
            json.dump(config, output, ensure_ascii=False, indent=2, allow_nan=False)
            output.write('\n')
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f'Inputs saved to {target}')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Import one model interactively or from a saved JSON configuration.')
    parser.add_argument('-i', '--input', type=Path, help='Saved import configuration; relative source paths use its directory')
    parser.add_argument('-f', '--force', action='store_true', help='Overwrite conflicting files and ES metadata without prompting')
    args = parser.parse_args(argv)
    if args.input:
        config_path = args.input.expanduser().resolve()
        config = json.loads(config_path.read_text(encoding='utf-8-sig'))
        directory = config_path.parent
    else:
        config = interactive_config()
        directory = Path.cwd()
    config = validate_config(config, directory)
    execute_config(config, force=args.force)
    # Config-driven runs never ask to save again, allowing unattended -i ... -f.
    if not args.input:
        try:
            save_config(config)
        except (OSError, ValueError) as exc:
            print(f'Import succeeded, but the configuration could not be saved: {exc}', file=sys.stderr)
            return 1
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print('\nInput/operation cancelled. If an import had started, inspect the server files and ES state.', file=sys.stderr)
        sys.exit(130)
    except (OSError, ValueError, RuntimeError, requests.RequestException) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)
