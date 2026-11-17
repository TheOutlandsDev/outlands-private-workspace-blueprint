import copy
from pathlib import Path
import unittest

from advisories import review, version
from runtime_io import load_json

HERE = Path(__file__).parent


class AdvisoryTests(unittest.TestCase):
    def setUp(self):
        self.data = load_json(HERE / 'fixtures/advisories.example.json')

    def test_exact_product_and_exclusive_fixed_boundary(self):
        report = review(self.data, '2026-01-01T12:00:00Z')
        self.assertEqual([x['status'] for x in report['results']],
                         ['REVIEW_CANDIDATE', 'NO_RANGE_MATCH', 'NO_RANGE_MATCH'])
        self.assertFalse(any(x['exposure_confirmed'] for x in report['results']))
        self.assertFalse(report['remediation_authorized'])

    def test_introduced_boundary_is_inclusive(self):
        self.data['assets'][0]['version'] = '1.1.0'
        self.assertEqual(review(self.data, '2026-01-01T00:00:00Z')['results'][0]['status'],
                         'REVIEW_CANDIDATE')

    def test_fresh_stale_and_future_are_distinct(self):
        self.assertEqual(review(self.data, '2026-01-02T00:00:00Z')['freshness'], 'FRESH')
        self.assertEqual(review(self.data, '2026-01-02T00:00:01Z')['freshness'], 'STALE')
        with self.assertRaises(ValueError):
            review(self.data, '2025-12-31T00:00:00Z')

    def test_unsupported_version_syntax_is_refused(self):
        for value in ['v1.2.0', '1.2', '1.2.0-rc1', '1.2.0+build', '01.2.3', '1:2.3.4', None]:
            with self.assertRaises(ValueError):
                version(value)
        self.assertGreater(version('1.10.0'), version('1.2.0'))

    def test_bad_range_duplicates_and_real_source_are_refused(self):
        mutations = [lambda d: d.update(synthetic_fixture=False),
                     lambda d: d['advisories'][0].update(fixed='1.0.0'),
                     lambda d: d['advisories'][0].update(source='https://example.com/advisory'),
                     lambda d: d['advisories'][0].update(source='https://user' + '@' + 'advisories.example.invalid/a'),
                     lambda d: d['assets'].append(copy.deepcopy(d['assets'][0]))]
        for mutate in mutations:
            data = copy.deepcopy(self.data)
            mutate(data)
            with self.assertRaises(ValueError):
                review(data, '2026-01-01T12:00:00Z')
