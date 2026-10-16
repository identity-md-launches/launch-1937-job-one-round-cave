import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
import abi_delta as delta


def fn(name='balanceOf', inputs=('address',), outputs=('uint256',), **extra):
    return dict(type='function', name=name, inputs=[{'type': t} for t in inputs],
                outputs=[{'type': t} for t in outputs], **extra)


class DeltaTests(unittest.TestCase):
    def test_return_change_preserves_selector(self):
        result = delta.compare([fn()], [fn(outputs=('uint128',))])
        self.assertEqual(result['changed'][0]['fields'], ['output_types'])
        self.assertEqual(result['changed'][0]['before']['selector'], '0x70a08231')
        self.assertEqual(result['changed'][0]['after']['selector'], '0x70a08231')

    def test_alias_names_order_and_ignored_entries(self):
        a = fn(outputs=('uint',))
        b = fn(); b['inputs'][0]['name'] = 'holder'
        result = delta.compare([a, fn('totalSupply', ())],
                               [fn('totalSupply', ()), b, {'type': 'receive'}])
        self.assertEqual(result['status'], 'no-function-differences')
        self.assertEqual(result['ignored_entry_counts']['after'], 1)

    def test_added_removed_overloads(self):
        result = delta.compare([fn('f', ('uint8',))], [fn('f', ('uint16',))])
        self.assertEqual(result['removed'][0]['signature'], 'f(uint8)')
        self.assertEqual(result['added'][0]['signature'], 'f(uint16)')

    def test_known_cross_revision_collision(self):
        result = delta.compare([fn('burn', ('uint256',), ())],
                               [fn('collate_propagate_storage', ('bytes16',), ())])
        self.assertEqual(result['selector_conflicts'], [{
            'selector': '0x42966c68', 'before': ['burn(uint256)'],
            'after': ['collate_propagate_storage(bytes16)']}])

    def test_unchanged_collision_requires_review(self):
        entries = [fn('burn', ('uint256',)), fn('collate_propagate_storage', ('bytes16',))]
        self.assertEqual(delta.compare(entries, entries)['status'], 'review-required')

    def test_duplicate_alias_refused(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            delta.compare([fn('f', ('uint',)), fn('f', ('uint256',))], [])

    def test_unknown_mutability_is_not_inferred(self):
        result = delta.compare([fn()], [fn(stateMutability='view')])
        self.assertEqual(result['changed'][0]['fields'], ['state_mutability'])
        self.assertIsNone(result['changed'][0]['before']['state_mutability'])
        for value in (None, {}, 'constant'):
            with self.assertRaises(ValueError):
                delta.compare([fn(stateMutability=value)], [])
        with self.assertRaises(ValueError):
            delta.compare([fn(constant=True)], [])

    def test_unsupported_inputs_or_outputs_refused(self):
        for entry in (fn(inputs=('uint[][]',)), fn(outputs=('string[]',))):
            with self.assertRaises(ValueError):
                delta.compare([entry], [])

    def test_nested_tuple_change(self):
        a = fn(); a['outputs'] = [{'type': 'tuple', 'components': [{'type': 'uint'}, {'type': 'string'}]}]
        b = copy.deepcopy(a); b['outputs'][0]['components'][0]['type'] = 'int'
        row = delta.compare([a], [b])['changed'][0]
        self.assertEqual(row['before']['output_types'], ['(uint256,string)'])
        self.assertEqual(row['after']['output_types'], ['(int256,string)'])

    def test_limits_and_invalid_input(self):
        for entries in ({}, [fn()] * 257, [{'type': 'function', 'name': 'x', 'outputs': {}}]):
            with self.assertRaises(ValueError):
                delta.compare(entries, [])

    def test_empty_and_deterministic(self):
        self.assertEqual(delta.compare([], [])['status'], 'no-function-differences')
        a, b = [fn('z'), fn('a')], [fn('c'), fn('b')]
        self.assertEqual(delta.compare(a, b), delta.compare(a[::-1], b[::-1]))

    def test_cli_demo_equal_and_missing(self):
        script = str(Path(delta.__file__))
        demo = subprocess.run([sys.executable, '-B', script, '--demo'], capture_output=True, text=True)
        self.assertEqual(demo.returncode, 1)
        self.assertEqual(json.loads(demo.stdout)['changed'][0]['signature'], 'balanceOf(address)')
        fixture = 'line-4/tools/selector-audit/erc20.json'
        equal = subprocess.run([sys.executable, '-B', script, '--before', fixture, '--after', fixture], capture_output=True, text=True)
        self.assertEqual(equal.returncode, 0)
        missing = subprocess.run([sys.executable, '-B', script, '--before', fixture, '--after', 'line-4/no-such-abi.json'], capture_output=True, text=True)
        self.assertEqual(missing.returncode, 2)
        self.assertEqual(missing.stdout, '')
        self.assertNotIn('Traceback', missing.stderr)


if __name__ == '__main__':
    unittest.main()
