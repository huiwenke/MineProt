import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from starlette.datastructures import UploadFile
from mineprot import import_ui, settings

PDB = b'ATOM      1  CA  ALA A   1      11.104  13.207  10.000  1.00 90.00           C  \nEND\n'


def upload(name, data):
    return UploadFile(filename=name, file=io.BytesIO(data))


def archive(files):
    buffer = io.BytesIO()
    with ZipFile(buffer, 'w') as zipped:
        for name, data in files.items():
            zipped.writestr(name, data)
    return upload('results.zip', buffer.getvalue())


class BrowserImportTests(unittest.TestCase):
    def test_single_matches_toolkit_and_renames_companions(self):
        form = dict(mode='single', repo='test', compression='gz', calculate_plddt='on',
                    structure=upload('original.pdb', PDB), json=upload('scores.json', b'{"plddt":[80,90]}'))
        with patch.object(import_ui, 'store', return_value={'status': 'imported'}) as store:
            import_ui.process(form)
        repo, document, batch, force = store.call_args.args
        self.assertEqual(document['name'], 'original')
        self.assertEqual(document['score'], 85)
        self.assertEqual(document['seq'], '')
        self.assertEqual(document['anno']['description'], ['original'])
        self.assertEqual([item['name'] for item, _ in batch], ['original.pdb', 'original.json'])
        self.assertTrue(all(item['storage'] == 'gzip' for item, _ in batch))

    def test_colabfold_relax_and_default_no_msa(self):
        files = {'job_unrelaxed_rank_001_model.pdb': PDB,
                 'job_relaxed_rank_001_model.pdb': PDB,
                 'job_scores_rank_001_model.json': b'{"plddt":[93]}',
                 'job.a3m': b'>query\nA\n>homolog\nA\n'}
        for relaxed in ('', 'on'):
            form = dict(mode='archive', system='colabfold', repo='test', relax=relaxed,
                        archive=archive(files))
            with patch.object(import_ui, 'store', return_value={'status': 'imported'}) as store:
                import_ui.process(form)
            _, document, batch, _ = store.call_args.args
            self.assertEqual(document['seq'], 'A')
            self.assertEqual(document['score'], 93)
            self.assertEqual([item['name'] for item, _ in batch], ['job.pdb', 'job.json'])

    def test_automatic_annotation_requires_and_stores_msa(self):
        files = {'job_unrelaxed_rank_001_model.pdb': PDB,
                 'job_scores_rank_001_model.json': b'{"plddt":[90]}'}
        form = dict(mode='archive', system='colabfold', repo='test', annotate='on', archive=archive(files),
                    homolog='ignored', database='ignored', description='ignored')
        with self.assertRaisesRegex(ValueError, 'requires A3M'):
            import_ui.process(form)
        files['job.a3m'] = b'>query\nA\n>sp|P12345|example\nA\n'
        form['archive'] = archive(files)
        annotation = {'homolog': 'P12345', 'database': 'uniprotkb', 'description': ['Example']}
        with patch('mineprot_toolkit.common.annotations.uniprot_to_mineprot', return_value=annotation), \
                patch.object(import_ui, 'store', return_value={'status': 'imported'}) as store:
            import_ui.process(form)
        _, document, batch, _ = store.call_args.args
        self.assertEqual(document['anno']['homolog'], 'P12345')
        self.assertIn('job.a3m', [item['name'] for item, _ in batch])

    def test_alphafold3_merges_confidence_files(self):
        import gemmi
        structure = gemmi.read_pdb_string(PDB.decode())
        cif = structure.make_mmcif_document().as_string()
        form = dict(mode='archive', system='alphafold3', repo='test', compression='gz',
                    homolog='P12345', database='uniprotkb', description='Manual description;Another description',
                    archive=archive({
            'nested/job_model.cif': cif,
            'nested/job_confidences.json': '{"atom_plddts":[87],"pae":[[0]]}',
            'nested/job_summary_confidences.json': '{"ptm":0.8}'}))
        with patch.object(import_ui, 'store', return_value={'status': 'imported'}) as store:
            import_ui.process(form)
        _, document, batch, _ = store.call_args.args
        self.assertEqual(document['score'], 87)
        self.assertEqual(document['anno'], {
            'homolog': 'P12345', 'database': 'uniprotkb',
            'description': ['Manual description', 'Another description', 'job', 'P12345']})
        import gzip
        merged = json.loads(gzip.decompress(batch[1][1]))
        self.assertEqual(merged['ptm'], 0.8)
        self.assertEqual(merged['pae'], [[0]])

    def test_zip_rejects_traversal_and_expansion(self):
        for files in ({'../escape': 'bad'}, {'large': 'x' * 100}):
            with tempfile.TemporaryDirectory() as root, patch.object(settings, 'MAX_BODY', 10):
                with self.assertRaises(ValueError):
                    import_ui.extract_zip(archive(files).file, Path(root))

    def test_rejects_invalid_repo_and_af3_colabfold_options(self):
        for form in (dict(mode='single', repo='../bad'),
                     dict(mode='archive', repo='test', system='alphafold3', relax='on')):
            with self.assertRaises(ValueError):
                import_ui.process(form)

    def test_storage_and_metadata_write_order(self):
        import gzip
        import httpx
        form = dict(mode='single', repo='test', compression='gz', name='saved',
                    structure=upload('input.pdb', PDB))
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(settings, 'REPO_ROOT', Path(directory) / 'repo'), \
                patch.object(settings, 'CACHE_ROOT', Path(directory) / 'cache'), \
                patch.object(import_ui.search, 'get_document', return_value={}), \
                patch.object(import_ui.search, 'clear_browse'), \
                patch.object(import_ui.search, 'es_request', return_value=httpx.Response(201, request=httpx.Request('PUT', 'http://es/test'))) as es:
            result = import_ui.process(form)
            self.assertEqual(result['results'][0]['status'], 'imported')
            self.assertEqual(gzip.decompress((Path(directory) / 'repo/test/saved.pdb.gz').read_bytes()), PDB)
            self.assertEqual(es.call_args.kwargs['json']['name'], 'saved')

    def test_conflicting_metadata_prevents_file_writes(self):
        form = dict(mode='single', repo='test', structure=upload('input.pdb', PDB))
        with patch.object(import_ui.search, 'get_document', return_value={'name': 'input', 'score': 99}), \
                patch.object(import_ui.imports, 'commit') as commit:
            with self.assertRaisesRegex(ValueError, 'metadata already exists'):
                import_ui.process(form)
            commit.assert_not_called()

    def test_fcz_rejects_multiple_chains_before_writes(self):
        second_chain = PDB.split(b'\n')[0].replace(b'ALA A', b'ALA B') + b'\nEND\n'
        form = dict(mode='single', repo='test', compression='fcz',
                    structure=upload('complex.pdb', PDB.replace(b'END\n', b'TER\n') + second_chain))
        with patch.object(import_ui, 'store') as store:
            with self.assertRaisesRegex(ValueError, 'multiple chains'):
                import_ui.process(form)
            store.assert_not_called()
