import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import initializer_csv as tool


class InitializerCSVTests(unittest.TestCase):
    def setUp(self):
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir='test/scratch')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'src'
        self.source.mkdir()

    def source_file(self, path, text):
        path = self.source / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def save(self, name, text):
        path = self.root / name
        path.write_text(text)
        return path

    def test_changed_initializer_bytes_are_reviewed_without_executing(self):
        self.source_file('main.py', 'raise RuntimeError("must not run")\nimport pkg.worker\n')
        init = self.source_file('pkg/__init__.py', 'raise RuntimeError("must not run")\n')
        self.source_file('pkg/worker.py', '')
        before, evidence = tool.snapshot(self.source)
        rows = list(csv.DictReader(io.StringIO(before)))
        base = json.loads(rows[0]['base_evidence'])
        self.assertEqual(base['source_sha256']['pkg/__init__.py'], hashlib.sha256(init.read_bytes()).hexdigest())
        self.assertEqual(evidence['summary']['base_initializer_sources'], 1)
        init.write_text('raise RuntimeError("still must not run")\n')
        after, _ = tool.snapshot(self.source)
        report = tool.compare(self.save('before.csv', before), self.save('after.csv', after))
        self.assertFalse(report['comparison']['equal'])
        self.assertIn('base_evidence', report['comparison']['changed'][0]['fields'])
        self.assertEqual(report['status_transitions']['columns'][0]['changed_rows'], 0)

    def test_missing_to_present_aggregates_status_and_retains_details(self):
        self.source_file('main.py', 'import pkg.worker\n')
        self.source_file('pkg/__init__.py', '')
        before, _ = tool.snapshot(self.source)
        self.source_file('pkg/worker.py', '')
        after, _ = tool.snapshot(self.source)
        r = tool.compare(self.save('b.csv', before), self.save('a.csv', after))
        self.assertEqual(r['status_transitions']['columns'][0]['transitions'],
                         [{'before': 'missing_source', 'after': 'source_candidate', 'rows': 1}])
        self.assertEqual(r['comparison']['summary']['changed'], 1)

    def test_conditional_child_chain_and_namespace_steps_retained(self):
        self.source_file('main.py', 'from ns.pkg import child\n')
        self.source_file('ns/pkg/__init__.py', 'child = 3\n')
        self.source_file('ns/pkg/child/__init__.py', '')
        text, _ = tool.snapshot(self.source)
        row = next(csv.DictReader(io.StringIO(text)))
        self.assertEqual(json.loads(row['base_evidence'])['steps'][0]['kind'], 'namespace_candidate')
        child = json.loads(row['conditional_evidence'])
        self.assertEqual(child['condition'], 'only_if_attribute_missing')
        self.assertEqual(len(child['initializers']), 2)
        self.assertIn('ns/pkg/child/__init__.py', child['source_sha256'])

    def test_same_line_alias_keys_line_shifts_and_empty_roots(self):
        file = self.source_file('main.py', 'import os, sys; import json\n')
        before, _ = tool.snapshot(self.source)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(before)))), 3)
        file.write_text('\nimport os, sys; import json\n')
        after, _ = tool.snapshot(self.source)
        r = tool.compare(self.save('b.csv', before), self.save('a.csv', after))
        self.assertEqual(r['comparison']['summary']['added'], 3)
        self.assertEqual(r['comparison']['summary']['removed'], 3)
        self.assertEqual(r['status_transitions']['columns'][0]['changed_rows'], 0)
        file.unlink()
        empty, _ = tool.snapshot(self.source)
        path = self.save('empty.csv', empty)
        self.assertTrue(tool.compare(path, path)['comparison']['equal'])

    def test_duplicate_keys_schema_and_invalid_coordinates_refused(self):
        self.source_file('main.py', 'import os\n')
        text, _ = tool.snapshot(self.source)
        rows = list(csv.DictReader(io.StringIO(text)))
        for field, value in [('line', '0'), ('column', '-1'), ('line', '01'), ('alias_index', 'x'), ('path', '')]:
            row = dict(rows[0], **{field: value})
            stream = io.StringIO(); writer = csv.DictWriter(stream, fieldnames=tool.COLUMNS)
            writer.writeheader(); writer.writerow(row)
            path = self.save('bad.csv', stream.getvalue())
            with self.assertRaises(ValueError):
                tool.compare(path, path)
        duplicate = self.save('dup.csv', text + text.splitlines(keepends=True)[1])
        with self.assertRaises(ValueError): tool.compare(duplicate, duplicate)
        schema = self.save('schema.csv', 'path,line,column,alias_index\na,1,0,0\n')
        with self.assertRaises(ValueError): tool.compare(schema, schema)

    def test_budget_refusal_no_partial_csv_and_warning_exit(self):
        self.source_file('main.py', 'import pkg\n')
        self.source_file('pkg/__init__.py', '')
        command = [sys.executable, '-B', str(Path(tool.__file__)), 'snapshot', str(self.source)]
        refused = subprocess.run(command + ['--max-files', '1'], capture_output=True, text=True, timeout=10)
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(refused.stdout, '')
        self.source_file('broken.py', 'def broken(\n')
        warning = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(warning.returncode, 1)
        self.assertTrue(warning.stdout.startswith(','.join(tool.COLUMNS)))
        self.assertEqual(json.loads(warning.stderr)['summary']['issues'], 1)

    def test_collision_evidence_and_self_equality_do_not_hide_warning(self):
        self.source_file('main.py', 'import pkg\n')
        self.source_file('pkg.py', '')
        self.source_file('pkg/__init__.py', '')
        text, evidence = tool.snapshot(self.source)
        self.assertEqual(evidence['issues'][0]['type'], 'module_collision')
        row = next(csv.DictReader(io.StringIO(text)))
        self.assertEqual(len(json.loads(row['base_evidence'])['source_sha256']), 2)
        path = self.save('same.csv', text)
        self.assertTrue(tool.compare(path, path)['comparison']['equal'])
        self.assertIn('does not certify', tool.SCOPE)


if __name__ == '__main__':
    unittest.main()
