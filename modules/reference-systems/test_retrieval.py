import copy
from pathlib import Path
import unittest

from retrieval import Index
from runtime_io import load_json

HERE = Path(__file__).parent


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.corpus = load_json(HERE / 'fixtures/corpus.example.json')
        self.index = Index(self.corpus)

    def test_authorization_filters_before_ranking(self):
        self.assertEqual(self.index.search('recovery', 'reader')['results'], [])
        result = self.index.search('recovery', 'owner')['results']
        self.assertEqual(result[0]['source_id'], 'fictional-owner-note')

    def test_untrusted_text_is_returned_without_execution(self):
        report = self.index.search('injection', 'reader')
        self.assertTrue(report['results'][0]['untrusted_source_text'])
        self.assertFalse(report['answer_generated'])

    def test_deletion_removes_all_chunks_and_does_not_grant_permission(self):
        with self.assertRaises(ValueError):
            self.index.delete('fictional-owner-note', 'reader')
        self.assertTrue(self.index.delete('fictional-owner-note', 'owner'))
        self.assertFalse(self.index.delete('fictional-owner-note', 'owner'))
        self.assertEqual(self.index.search('recovery', 'owner')['results'], [])

    def test_mutating_source_metadata_cannot_change_permissions(self):
        self.corpus['documents'][1]['audience'].append('reader')
        self.assertEqual(self.index.search('recovery', 'reader')['results'], [])

    def test_admission_refuses_unknown_fields_rights_and_claims(self):
        mutations = [lambda d: d.update(synthetic_fixture=False),
                     lambda d: d.update(schema_version=True),
                     lambda d: d['documents'][0].update(admitted=False),
                     lambda d: d['documents'][0].update(rights='unknown'),
                     lambda d: d['documents'][0].update(audience=['admin']),
                     lambda d: d['documents'][0].update(path='fictional'),
                     lambda d: d['documents'].append(copy.deepcopy(d['documents'][0]))]
        for mutate in mutations:
            data = copy.deepcopy(self.corpus)
            mutate(data)
            with self.assertRaises(ValueError):
                Index(data)

    def test_query_limits_unknown_roles_and_empty_matches(self):
        for query, role, limit in [('', 'owner', 3), ('x' * 257, 'owner', 3),
                                   ('lamp', 'admin', 3), ('lamp', 'reader', True),
                                   ('lamp', 'reader', 6)]:
            with self.assertRaises(ValueError):
                self.index.search(query, role, limit)
        self.assertEqual(self.index.search('nonexistent', 'reader')['results'], [])

    def test_chunk_bound_and_determinism(self):
        self.corpus['documents'][0]['text'] = 'lamp ' * 100
        index = Index(self.corpus)
        hits = index.search('lamp', 'reader', 5)['results']
        self.assertTrue(all(len(hit['text']) <= 240 for hit in hits))
        self.assertEqual(hits, index.search('lamp', 'reader', 5)['results'])
