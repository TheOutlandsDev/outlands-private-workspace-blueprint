import copy
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parent
SPEC = importlib.util.spec_from_file_location('workspace_plan', ROOT / 'workspace_plan.py')
planner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(planner)


class WorkspacePlanTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'systems.example.json').read_text())

    def test_profiles_are_ordered_and_never_accepted(self):
        for profile in sorted(planner.PROFILES):
            plan = planner.make_plan(self.data, profile)
            seen = set()
            for step in plan['steps']:
                self.assertTrue(set(step['requires']) <= seen)
                self.assertNotIn(step['system'], seen)
                seen.add(step['system'])
                self.assertEqual(set(step['acceptance'].values()), {'NOT_RUN'})
            self.assertFalse(plan['deployment_authorized'])
        self.assertEqual(len(planner.make_plan(self.data, 'extended')['steps']), 10)
        self.assertEqual(len(planner.make_plan(self.data, 'minimal')['steps']), 3)

    def test_synthetic_runtime_coverage_survives_without_live_acceptance(self):
        plan = planner.make_plan(self.data, 'extended')
        retrieval = next(s for s in plan['steps'] if s['system'] == 'retrieval')
        self.assertEqual(retrieval['coverage'], 'SYNTHETIC_RUNTIME')
        self.assertEqual(set(retrieval['acceptance'].values()), {'NOT_RUN'})

    def test_cycle_outside_selected_profile_is_refused(self):
        self.data['systems'][-1]['requires'] = ['security-review']
        with self.assertRaises(ValueError):
            planner.make_plan(self.data, 'minimal')

    def test_missing_duplicate_and_malformed_dependencies(self):
        for value in [['missing'], ['ai', 'ai'], [3], 'ai']:
            data = copy.deepcopy(self.data)
            data['systems'][-1]['requires'] = value
            with self.assertRaises(ValueError):
                planner.make_plan(data)

    def test_no_state_or_operator_fields_are_admitted(self):
        mutations = [
            lambda d: d.update(synthetic_fixture=False),
            lambda d: d.update(schema_version=True),
            lambda d: d.update(operator='fictional'),
            lambda d: d['systems'][0].update(acceptance='PASS'),
            lambda d: d['systems'][0].update(coverage='DEPLOYED'),
            lambda d: d['systems'].append(copy.deepcopy(d['systems'][0])),
            lambda d: d['profiles'].update(workspace=['unknown']),
        ]
        for mutate in mutations:
            data = copy.deepcopy(self.data)
            mutate(data)
            with self.assertRaises(ValueError):
                planner.make_plan(data)

    def test_duplicate_json_keys_are_refused(self):
        with self.assertRaises(ValueError):
            json.loads('{"schema_version":1,"schema_version":1}',
                       object_pairs_hook=planner.unique_object)

    def test_cli_refuses_unknown_input_without_echo(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(planner.main(['fictional-private-marker']), 1)
        self.assertNotIn('fictional-private-marker', output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['result'], 'REVIEW')

    def test_cli_does_not_probe_host_or_network(self):
        with patch('socket.socket', side_effect=AssertionError('network')), \
             patch('subprocess.run', side_effect=AssertionError('subprocess')):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(planner.main([]), 0)
        self.assertEqual(json.loads(output.getvalue()), planner.make_plan(self.data))


if __name__ == '__main__':
    unittest.main()
