import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('initializers_tested', HERE / 'initializers.py')
TOOL = importlib.util.module_from_spec(spec)
spec.loader.exec_module(TOOL)
MAPPER = TOOL.load_budget().load_mapper()


class InitializerTests(unittest.TestCase):
    def inspect(self, sources):
        return TOOL.inspect_sources({p: s.encode() if isinstance(s, str) else s
                                     for p, s in sources.items()}, MAPPER)

    def test_nested_import_order_and_no_execution(self):
        result = self.inspect({'main.py': 'raise RuntimeError()\nimport pkg.sub.worker',
                               'pkg/__init__.py': '', 'pkg/sub/__init__.py': '',
                               'pkg/sub/worker.py': ''})
        site = result['sites'][0]
        self.assertEqual(site['line'], 2)
        self.assertEqual([p['module'] for p in site['base']['initializers']], ['pkg', 'pkg.sub'])
        self.assertEqual(result['summary']['base_initializer_sources'], 2)

    def test_namespace_has_no_initializer(self):
        result = self.inspect({'main.py': 'import ns.pkg.worker',
                               'ns/pkg/__init__.py': '', 'ns/pkg/worker.py': ''})
        base = result['sites'][0]['base']
        self.assertEqual(base['steps'][0]['kind'], 'namespace_candidate')
        self.assertEqual([p['module'] for p in base['initializers']], ['ns.pkg'])

    def test_from_child_is_conditional(self):
        site = self.inspect({'main.py': 'from pkg import child', 'pkg/__init__.py': 'child = 3',
                             'pkg/child/__init__.py': ''})['sites'][0]
        self.assertEqual([p['module'] for p in site['base']['initializers']], ['pkg'])
        self.assertEqual(site['child_candidate']['condition'], 'only_if_attribute_missing')
        self.assertEqual([p['module'] for p in site['child_candidate']['initializers']], ['pkg', 'pkg.child'])

    def test_symbol_import_from_module_does_not_guess_child(self):
        site = self.inspect({'main.py': 'from pkg.mod import value', 'pkg/__init__.py': '',
                             'pkg/mod.py': 'value = 3'})['sites'][0]
        self.assertIsNone(site['child_candidate'])
        self.assertEqual([p['module'] for p in site['base']['initializers']], ['pkg'])

    def test_relative_import_and_too_many_dots(self):
        sites = self.inspect({'pkg/__init__.py': '', 'pkg/sub/worker.py':
                              'from .. import child\nfrom ... import missing',
                              'pkg/child/__init__.py': ''})['sites']
        self.assertEqual(sites[0]['base']['target'], 'pkg')
        self.assertEqual(sites[0]['child_candidate']['target'], 'pkg.child')
        self.assertEqual(sites[1]['base']['status'], 'unresolved_relative')
        self.assertEqual(sites[1]['base']['initializers'], [])

    def test_parent_module_blocks_descendant(self):
        site = self.inspect({'main.py': 'import pkg.sub.worker', 'pkg/__init__.py': '',
                             'pkg/sub.py': '', 'pkg/sub/worker.py': ''})['sites'][0]
        self.assertEqual(site['base']['status'], 'blocked_by_source_module')
        self.assertEqual([p['module'] for p in site['base']['steps']], ['pkg', 'pkg.sub'])
        self.assertEqual([p['module'] for p in site['base']['initializers']], ['pkg'])

    def test_missing_descendant_retains_earlier_package_candidate(self):
        site = self.inspect({'main.py': 'import pkg.absent', 'pkg/__init__.py': ''})['sites'][0]
        self.assertEqual(site['base']['status'], 'missing_source')
        self.assertEqual(site['base']['initializers'], [{'module': 'pkg', 'path': 'pkg/__init__.py'}])

    def test_collision_prefers_regular_package_reports_shadowing(self):
        result = self.inspect({'main.py': 'import pkg.child', 'pkg.py': 'import hidden',
                               'pkg/__init__.py': '', 'pkg/child.py': ''})
        self.assertEqual(len(result['sites']), 1)
        self.assertEqual(result['issues'][0]['type'], 'module_collision')
        self.assertEqual(result['sites'][0]['base']['status'], 'source_candidate')
        self.assertEqual(result['sites'][0]['base']['steps'][0]['source_paths'], ['pkg.py', 'pkg/__init__.py'])

    def test_parse_issues_and_encoding(self):
        result = self.inspect({'bad.py': b'\x00', 'main.py': b'\xef\xbb\xbfimport pkg',
                               'pkg/__init__.py': b'# coding: latin-1\n# caf\xe9\n'})
        self.assertEqual(result['summary']['issues'], 1)
        self.assertEqual(result['sites'][0]['base']['initializers'][0]['module'], 'pkg')

    def test_multiple_aliases_same_line_and_wildcard(self):
        sites = self.inspect({'main.py': 'import a as x, b as y; from a import *',
                              'a/__init__.py': '', 'b/__init__.py': ''})['sites']
        self.assertEqual([s['spelling'] for s in sites], ['a', 'b', 'a import *'])
        self.assertEqual([s['alias_index'] for s in sites], [0, 1, 0])
        self.assertIsNone(sites[-1]['child_candidate'])
        self.assertGreater(sites[-1]['column'], 0)

    def test_root_initializer_is_not_named_package(self):
        result = self.inspect({'__init__.py': 'import hidden', 'worker.py': 'import pkg',
                               'pkg/__init__.py': ''})
        self.assertEqual(len(result['sites']), 1)
        self.assertEqual(result['sites'][0]['module'], 'worker')

    def test_cli_manifest_budget_and_strict_exits(self):
        scratch = Path.cwd() / 'test' / 'scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            root = Path(folder)
            (root / 'main.py').write_text('raise RuntimeError()\nimport pkg\n')
            (root / 'pkg').mkdir()
            (root / 'pkg' / '__init__.py').write_text('')
            command = [sys.executable, '-B', str(HERE / 'initializers.py'), str(root), '--json']
            ok = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            report = json.loads(ok.stdout)
            self.assertEqual(report['inventory']['files'], 2)
            self.assertEqual(len(report['inventory']['manifest'][0]['sha256']), 64)
            refused = subprocess.run(command + ['--max-files', '1'], capture_output=True, text=True)
            self.assertEqual(refused.returncode, 2)
            self.assertEqual(json.loads(refused.stdout)['error']['type'], 'budget_exceeded')
            (root / 'bad.py').write_bytes(b'\x00')
            strict = subprocess.run(command + ['--strict'], capture_output=True, text=True)
            self.assertEqual(strict.returncode, 1)

    def test_external_and_dynamic_calls_do_not_invent_initializers(self):
        result = self.inspect({'main.py': 'import json\n__import__("pkg")', 'pkg/__init__.py': ''})
        self.assertEqual(len(result['sites']), 1)
        self.assertEqual(result['sites'][0]['base']['initializers'], [])
        self.assertEqual(result['sites'][0]['base']['status'], 'missing_source')

    def test_conditional_nested_imports_remain_candidates(self):
        sites = self.inspect({'main.py': 'if False:\n import pkg\ndef later():\n import pkg',
                              'pkg/__init__.py': ''})['sites']
        self.assertEqual([s['line'] for s in sites], [2, 4])
        self.assertTrue(all(s['base']['initializers'] for s in sites))


if __name__ == '__main__':
    unittest.main()
