import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('probe_contract', HERE / 'probe_contract.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.r = json.loads((HERE / 'observed-before.json').read_text())

    def test_real_observation(self):
        self.assertEqual(m.compare(self.r, self.r)['verdict'], 'still_healthy')

    def test_transitions(self):
        failed = copy.deepcopy(self.r)
        p = failed['observation']['probe']
        failed['observation']['ok'] = p['ok'] = False
        p['checks'][0]['ok'] = False
        p['checks'][0]['actual'] = p['hops'][-1]['status'] = 503
        self.assertEqual(m.compare(self.r, failed)['verdict'], 'regressed')
        self.assertEqual(m.compare(failed, self.r)['verdict'], 'recovered')
        self.assertEqual(m.compare(failed, failed)['verdict'], 'still_failing')

    def test_value_types_and_null_recorded(self):
        a, b = copy.deepcopy(self.r), copy.deepcopy(self.r)
        for r in (a, b):
            r['contract']['compare_value'] = True
            r['observation']['probe']['checks'].append({'name': 'json_value', 'path': r['contract']['path'], 'ok': True})
        a['contract']['value'], b['contract']['value'] = True, 1
        self.assertEqual(m.compare(a, b)['changed_contract_fields'], ['value'])
        a['contract']['value'] = None
        self.assertEqual(m.compare(a, b)['verdict'], 'inconclusive')

    def test_deadline_and_producer_differences(self):
        for field in ('deadline_seconds', 'producer_sha256'):
            other = copy.deepcopy(self.r)
            if field == 'deadline_seconds':
                other['contract'][field] = 9
            else:
                other['contract'][field]['endpoint'] = 'a' * 64
            self.assertEqual(m.compare(self.r, other)['changed_contract_fields'], [field])

    def test_interrupted_observation(self):
        other = copy.deepcopy(self.r)
        other['observation'] = {'ok': False, 'error': {'kind': 'deadline'}}
        self.assertEqual(m.compare(self.r, other)['verdict'], 'inconclusive')

    def test_early_network_failure_comparable(self):
        other = copy.deepcopy(self.r)
        p = other['observation']['probe']
        other['observation']['ok'] = p['ok'] = False
        p.update(hops=[], checks=[], error={'kind': 'dns'})
        self.assertEqual(m.compare(self.r, other)['verdict'], 'regressed')

    def test_contradictory_settings(self):
        for field, value in [('url', 'https://api.imd.fun/other'), ('status', 201), ('path', '/other'), ('max_bytes', 100)]:
            other = copy.deepcopy(self.r)
            other['contract'][field] = value
            with self.assertRaises(ValueError):
                m.admitted(other)

    def test_unrequested_checks_refused(self):
        self.r['contract']['json'] = False
        self.r['contract']['path'] = None
        with self.assertRaises(ValueError):
            m.admitted(self.r)

    def test_invalid_spec(self):
        for field, value in [('timeout_seconds', True), ('deadline_seconds', float('nan')), ('max_bytes', False), ('path', '/a~2'), ('url', 'https://user:pass@api.imd.fun')]:
            s = copy.deepcopy(self.r['contract'])
            s[field] = value
            with self.assertRaises(ValueError):
                m.validate_spec(s)

    def test_command_matches_spec(self):
        s = self.r['contract']
        s.update(compare_value=True, value={'healthy': True})
        seen = []
        def fake(command, deadline):
            seen.extend(command)
            self.assertEqual(deadline, s['deadline_seconds'])
            return {'ok': False, 'error': {'kind': 'deadline'}}, 1
        report, code = m.capture(s, fake)
        self.assertIn('--expect-value={"healthy":true}', seen)
        self.assertIn('--expect-path=/launches/0/status', seen)
        self.assertIn('-I', seen)
        self.assertEqual(code, 1)
        self.assertEqual(report['contract'], s)

    def test_body_change_is_informational(self):
        other = copy.deepcopy(self.r)
        other['observation']['probe']['hops'][0]['body_sha256'] = 'a' * 64
        result = m.compare(self.r, other)
        self.assertEqual(result['verdict'], 'still_healthy')
        self.assertFalse(result['body_change_is_health_failure'])

    def test_cli_and_input_admission(self):
        run = subprocess.run([sys.executable, '-B', str(HERE / 'probe_contract.py'),
            'compare', str(HERE / 'observed-before.json'), str(HERE / 'observed-before.json')],
            capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)['verdict'], 'still_healthy')
        for raw in ('{"a":1,"a":2}', 'NaN', '1e999'):
            with self.assertRaises(ValueError):
                m.delta.strict_json(raw)
        with self.assertRaises(ValueError):
            m.delta.load('/outside-workspace/report.json')


if __name__ == '__main__':
    unittest.main()
