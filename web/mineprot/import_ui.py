"""Browser imports using the same preparation rules as the toolkit."""
# ruff: noqa: E402 -- toolkit source path is shared by checkout and Docker image.
import base64
import io
from pathlib import Path
import sys
import tempfile
from urllib.parse import quote
from zipfile import BadZipFile, ZipFile

import httpx

from . import imports, search, settings
from .storage import bounded_gunzip, component

# The Docker image and source checkout keep the toolkit beside web/.
TOOLKIT = Path(__file__).resolve().parents[2] / 'toolkit' / 'src'
if str(TOOLKIT) not in sys.path:
    sys.path.insert(0, str(TOOLKIT))

from mineprot_toolkit import import_single as single
from mineprot_toolkit.ai.alphafold3.transform import transform_directory, has_models
from mineprot_toolkit.ai.colabfold.transform import prediction_filename
from mineprot_toolkit.common.sequences import structure_sequence
from mineprot_toolkit.common.structures import load_structure


def flag(form, key):
    value = form.get(key, '')
    if value not in ('', 'on'):
        raise ValueError('Invalid option: ' + key)
    return value == 'on'


def extract_zip(upload, root):
    """Bound expanded bytes, reject traversal, links, and duplicate member paths."""
    try:
        with ZipFile(upload) as archive:
            entries = archive.infolist()
            if len(entries) > 10000 or sum(item.file_size for item in entries) > settings.MAX_BODY:
                raise ValueError('Expanded ZIP exceeds server limits')
            seen = set()
            total = 0
            for item in entries:
                path = Path(item.filename)
                target = (root / path).resolve()
                if ('\\' in item.filename or not target.is_relative_to(root.resolve())
                        or (item.external_attr >> 16) & 0o170000 == 0o120000):
                    raise ValueError('Unsafe ZIP member')
                if target in seen:
                    raise ValueError('Duplicate ZIP member')
                seen.add(target)
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item) as source, target.open('wb') as destination:
                    while chunk := source.read(65536):
                        total += len(chunk)
                        if total > settings.MAX_BODY:
                            raise ValueError('Expanded ZIP exceeds server limits')
                        destination.write(chunk)
    except BadZipFile as exc:
        raise ValueError('Please upload a valid ZIP archive') from exc


def config(form, structure, confidence=None, msa=None):
    return single.validate_config({
        'url': 'http://localhost', 'repo': str(form.get('repo', '')).strip(),
        'structure': str(structure), 'json': str(confidence) if confidence else None,
        'msa': str(msa) if msa else None, 'compression': form.get('compression', 'plain'),
        'calculate_plddt': flag(form, 'calculate_plddt'),
        'name': str(form.get('name', '')).strip() or structure.stem,
        'homolog': str(form.get('homolog', '')), 'database': form.get('database', ''),
        'description': str(form.get('description', '')),
    }, structure.parent)


def store(repo, document, batch, force):
    document_id = base64.b64encode(document['name'].encode()).decode()
    previous = search.get_document(repo, document_id)
    if previous and previous != document and not force:
        raise ValueError('Different metadata already exists; enable overwrite to replace it')
    body = {'repo': repo, 'force': force, 'files': [item for item, _ in batch]}
    checked = imports.check(body)['results']
    if any(item['status'] not in ('upload', 'unchanged') for item in checked):
        raise ValueError('File preflight failed: ' + str(checked))
    result = imports.commit(body, [io.BytesIO(data) for _, data in batch])['results']
    if any(item['status'] not in ('imported', 'unchanged') for item in result):
        raise ValueError('File import incomplete; metadata was not written: ' + str(result))
    with imports.locked(repo):
        current = search.get_document(repo, document_id)
        if not force and current not in ({}, previous, document):
            raise ValueError('Metadata changed during upload; files saved, metadata not written')
        response = search.es_request('PUT', quote(repo, safe='') + '/_doc/' + quote(document_id, safe=''),
                                     json=document)
        response.raise_for_status()
    search.clear_browse(repo)
    return {'name': document['name'], 'status': 'imported', 'files': result}


def process(form):
    mode = form.get('mode')
    if mode not in ('single', 'archive'):
        raise ValueError('Invalid import mode')
    single.validate_repo(str(form.get('repo', '')).strip())
    force = flag(form, 'force')
    with tempfile.TemporaryDirectory(prefix='mineprot-import-') as temporary:
        root = Path(temporary)
        if mode == 'single':
            paths = {}
            for key, suffixes in (('structure', ('.pdb', '.cif', '.mmcif')),
                                  ('json', ('.json',)), ('msa', ('.a3m',))):
                upload = form.get(key)
                if not getattr(upload, 'filename', ''):
                    if key == 'structure':
                        raise ValueError('A structure file is required')
                    continue
                name = component(upload.filename)
                if name.lower().endswith('.gz'):
                    name = name[:-3]
                    data = bounded_gunzip(upload.file.read(settings.MAX_BODY + 1))
                else:
                    data = upload.file.read(settings.MAX_BODY + 1)
                if Path(name).suffix.lower() not in suffixes or not data or len(data) > settings.MAX_BODY:
                    raise ValueError('Invalid ' + key + ' file')
                paths[key] = root / (key + Path(name).suffix.lower())
                paths[key].write_bytes(data)
            values = dict(form)
            if not str(form.get('name', '')).strip():
                values['name'] = single.logical_path(Path(form['structure'].filename)).stem
            options = config(values, paths['structure'], paths.get('json'), paths.get('msa'))
            document, batch = single.prepare_config(options)
            return {'results': [store(options['repo'], document, batch, force)]}

        system = form.get('system')
        if system not in ('alphafold3', 'colabfold'):
            raise ValueError('Invalid prediction system')
        relaxed, annotate = flag(form, 'relax'), flag(form, 'annotate')
        if system != 'colabfold' and (relaxed or annotate):
            raise ValueError('Relaxed results and automatic annotation apply to ColabFold only')
        upload = form.get('archive')
        if not getattr(upload, 'filename', '').lower().endswith('.zip'):
            raise ValueError('A ZIP archive is required')
        extracted, output = root / 'input', root / 'output'
        extracted.mkdir()
        output.mkdir()
        extract_zip(upload.file, extracted)
        if system == 'alphafold3':
            seen = set()
            directories = sorted({p.parent for p in extracted.rglob('*.cif') if has_models(p.parent)})
            if not directories:
                raise ValueError('No AlphaFold3 models found in ZIP')
            for directory in directories:
                transform_directory(directory, output, seen=seen)
            structures = sorted(output.glob('*.cif'))
        else:
            for path in sorted(extracted.rglob('*')):
                if not path.is_file():
                    continue
                name = prediction_filename(relaxed, path.name)
                if not name or (name.endswith('.a3m') and not annotate):
                    continue
                target = output / component(name)
                if target.exists():
                    raise ValueError('Duplicate ColabFold result: ' + name)
                target.write_bytes(path.read_bytes())
            structures = sorted(output.glob('*.pdb'))
            if not structures:
                raise ValueError('No matching ColabFold rank 1 models; check the relaxed option')
        if len(structures) > 80:
            raise ValueError('Import up to 80 models per archive')
        prepared = []
        for path in structures:
            confidence = path.with_suffix('.json')
            msa = path.with_suffix('.a3m')
            if not confidence.is_file():
                raise ValueError('Missing confidence JSON for ' + path.stem)
            if annotate and not msa.is_file():
                raise ValueError('Automatic annotation requires A3M for ' + path.stem)
            values = dict(form)
            values.update(name=path.stem, calculate_plddt='on')
            if annotate:
                values.update(homolog='', database='', description='')
            options = config(values, path, confidence, msa if annotate else None)
            document, batch = single.prepare_config(options)
            document['seq'] = structure_sequence(load_structure(path)[0])
            if annotate:
                from mineprot_toolkit.common.annotations import uniprot_to_mineprot
                identifiers = [line for line in msa.read_text().splitlines() if line.startswith('>')]
                document['anno'] = uniprot_to_mineprot(identifiers[1:], 10)
                if path.stem not in document['anno']['description']:
                    document['anno']['description'].append(path.stem)
            prepared.append((document, batch))
        results = []
        for document, batch in prepared:
            try:
                results.append(store(options['repo'], document, batch, force))
            except (ValueError, RuntimeError, OSError, httpx.HTTPError) as exc:
                results.append({'name': document['name'], 'status': 'error', 'error': str(exc)})
        return {'results': results}
