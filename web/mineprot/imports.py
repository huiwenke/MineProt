"""Batch import protocol and storage-format checks shared with legacy URLs."""
from contextlib import contextmanager
import fcntl
import gzip
import hashlib
import re

from . import search, settings
from .storage import atomic_write, bounded_gunzip, component, repo_file
from .foldcomp_worker import Validator

MAX_FILES = 256


def entry(value):
    if not isinstance(value, dict):
        raise ValueError('File entry must be an object')
    if not isinstance(value.get('name'), str):
        raise ValueError('File name must be a string')
    name = component(value['name'])
    storage = value['storage']
    if name.endswith('.fcz.gz'):
        raise ValueError('FCZ + gzip storage is not supported')
    suffix = name.rsplit('.', 1)[-1]
    if suffix not in ('pdb', 'cif', 'json', 'a3m', 'fcz'):
        raise ValueError('Unsupported import file type')
    if storage not in ('plain', 'gzip', 'fcz'):
        raise ValueError('Invalid storage format')
    if (suffix == 'fcz') != (storage == 'fcz'):
        raise ValueError('FCZ must use .fcz and cannot use gzip')
    return name, storage


def manifest(body):
    if not isinstance(body, dict):
        raise ValueError('Manifest must be an object')
    if not isinstance(body.get('repo'), str):
        raise ValueError('Repository name must be a string')
    component(body['repo'])
    if not isinstance(body.get('force', False), bool):
        raise ValueError('force must be a boolean')
    files = body['files']
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
        raise ValueError('A batch must contain 1 to 256 files')
    seen = set()
    for item in files:
        name, storage = entry(item)
        # PDB and FCZ share a logical structure name.
        key = name.rsplit('.', 1)[0] + '.structure' if name.endswith(('.pdb', '.fcz')) else name
        if key in seen:
            raise ValueError('Duplicate logical file in batch: ' + name)
        seen.add(key)
        if not isinstance(item.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', item['sha256']):
            raise ValueError('Invalid SHA-256')
        if storage == 'fcz' and (not isinstance(item.get('content_sha256'), str) or
                                 not re.fullmatch('[0-9a-f]{64}', item['content_sha256'])):
            raise ValueError('FCZ requires decoded-content SHA-256')
        if type(item.get('size')) is not int or item['size'] < 0:
            raise ValueError('Invalid file size')
        if item.get('encoding', 'identity') not in ('identity', 'gzip'):
            raise ValueError('Invalid transport encoding')
        if storage == 'fcz' and item.get('encoding', 'identity') != 'identity':
            raise ValueError('FCZ cannot use gzip transport')
    return body


@contextmanager
def locked(repo):
    directory = settings.CACHE_ROOT / 'import-locks'
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / (hashlib.sha256(repo.encode()).hexdigest() + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def existing(repo, name, storage):
    if name.endswith(('.pdb', '.fcz')):
        stem = name.rsplit('.', 1)[0]
        candidates = [(stem + '.pdb', 'plain'), (stem + '.pdb.gz', 'gzip'),
                      (stem + '.fcz', 'fcz'), (stem + '.fcz.gz', 'unsupported')]
    else:
        candidates = [(name, 'plain'), (name + '.gz', 'gzip')]
    found = [(repo_file(repo, candidate), kind) for candidate, kind in candidates
             if repo_file(repo, candidate).exists()]
    if len(found) > 1:
        raise ValueError('Multiple server storage formats exist for ' + name)
    if not found:
        return None
    path, actual = found[0]
    if actual == 'unsupported':
        raise ValueError('Server uses unsupported .fcz.gz storage for ' + name)
    if actual != storage:
        hint = {'plain': 'remove -z; use a regular PDB mode for PDB files',
                'gzip': 'use -z with a regular mode', 'fcz': 'use -m 4'}[actual]
        raise ValueError('Server storage is ' + actual + ' for ' + name + '; ' + hint)
    return path


def logical_bytes(path, storage):
    data = path.read_bytes()
    return bounded_gunzip(data) if storage == 'gzip' else data


def inspect(repo, item, force, validator):
    name, storage = entry(item)
    if item['size'] > settings.MAX_BODY:
        raise ValueError('File exceeds server size limit')
    path = existing(repo, name, storage)
    if path is None:
        return 'upload'
    digest = (validator.validate(path.read_bytes()) if storage == 'fcz' else
              hashlib.sha256(logical_bytes(path, storage)).hexdigest())
    if digest == (item['content_sha256'] if storage == 'fcz' else item['sha256']):
        return 'unchanged'
    return 'upload' if force else 'exists'


def check(body):
    manifest(body)
    results = []
    with Validator() as validator, locked(body['repo']):
        for item in body['files']:
            try:
                results.append({'name': item['name'], 'status': inspect(body['repo'], item, body.get('force', False), validator)})
            except (ValueError, RuntimeError, OSError, EOFError) as exc:
                results.append({'name': item['name'], 'status': 'error', 'error': str(exc)})
    return {'results': results, 'max_files': MAX_FILES, 'max_body_bytes': settings.MAX_BODY}


def commit(body, uploads):
    """Validate and commit independently; retries recognize already-written content."""
    manifest(body)
    if len(uploads) != len(body['files']):
        raise ValueError('Uploaded file count does not match manifest')
    results = []
    changed = False
    repo = body['repo']
    try:
        with Validator() as validator:
            for item, upload in zip(body['files'], uploads):
                name, storage = entry(item)
                try:
                    # Avoid decoding payloads that cannot be committed.
                    with locked(repo):
                        status = inspect(repo, item, body.get('force', False), validator)
                    if status == 'upload':
                        payload = upload.read(settings.MAX_BODY + 1)
                        if len(payload) > settings.MAX_BODY:
                            raise ValueError('File exceeds size limit')
                        encoded = item.get('encoding', 'identity') == 'gzip'
                        data = bounded_gunzip(payload) if encoded else payload
                        if len(data) != item['size'] or hashlib.sha256(data).hexdigest() != item['sha256']:
                            raise ValueError('File length or SHA-256 mismatch')
                        if storage == 'fcz':
                            if validator.validate(data) != item['content_sha256']:
                                raise ValueError('Decoded FCZ content checksum mismatch')
                        with locked(repo):
                            status = inspect(repo, item, body.get('force', False), validator)
                            if status == 'upload':
                                target = repo_file(repo, name + '.gz' if storage == 'gzip' else name)
                                stored = (payload if encoded else gzip.compress(data, mtime=0)) if storage == 'gzip' else data
                                atomic_write(target, stored)
                                status = 'imported'
                                changed = True
                    results.append({'name': name, 'status': status})
                except (ValueError, RuntimeError, OSError, EOFError) as exc:
                    results.append({'name': name, 'status': 'error', 'error': str(exc)})
    finally:
        if changed:
            search.clear_browse(repo)
    return {'results': results}
