#!/usr/bin/env python3
"""Compare supported function interfaces in two local Ethereum ABIs offline."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

SOURCE = Path(__file__).resolve().parents[1] / 'selector-audit' / 'selector_audit.py'
spec = importlib.util.spec_from_file_location('line4_delta_inventory', SOURCE)
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)
codec = inventory.abi
MAX_FUNCTIONS = 256


def snapshot(entries):
    codec.validate_abi(entries)
    functions = [entry for entry in entries if entry['type'] == 'function']
    if len(functions) > MAX_FUNCTIONS:
        raise ValueError('ABI exceeds 256 function entries')
    result = {}
    for entry in functions:
        signature = codec.input_signature(entry)
        if len(signature) > codec.MAX_FUNCTION_REFERENCE:
            raise ValueError('canonical signature exceeds 8192 characters')
        codec.check_type_tree(entry.get('outputs', []))
        outputs = [codec.canonical(p) for p in entry.get('outputs', [])]
        mutability = entry.get('stateMutability')
        if 'stateMutability' in entry and mutability not in ('pure', 'view', 'nonpayable', 'payable'):
            raise ValueError('invalid function stateMutability')
        # Do not silently interpret legacy flags as modern mutability metadata.
        if 'constant' in entry or 'payable' in entry:
            raise ValueError('legacy constant/payable flags are unsupported; supply stateMutability')
        if signature in result:
            raise ValueError('duplicate canonical function signature: ' + signature)
        result[signature] = {'selector': '0x' + codec.keccak256(signature.encode('ascii'))[:4].hex(),
                             'output_types': outputs, 'state_mutability': mutability}
    return result


def compare(before, after):
    old, new = snapshot(before), snapshot(after)
    removed = sorted(old.keys() - new.keys())
    added = sorted(new.keys() - old.keys())
    changed, unchanged = [], []
    for signature in sorted(old.keys() & new.keys()):
        fields = [field for field in ('output_types', 'state_mutability')
                  if old[signature][field] != new[signature][field]]
        if fields:
            changed.append({'signature': signature, 'fields': fields,
                            'before': old[signature], 'after': new[signature]})
        else:
            unchanged.append(signature)
    # Include both revisions: a removed function and its replacement can share
    # a selector even when neither revision has an internal collision.
    selectors = {}
    for signature, row in {**old, **new}.items():
        selectors.setdefault(row['selector'], set()).add(signature)
    conflicts = []
    for selector, signatures in sorted(selectors.items()):
        if len(signatures) > 1:
            conflicts.append({'selector': selector, 'before': sorted(s for s in signatures if s in old),
                              'after': sorted(s for s in signatures if s in new)})
    review = bool(removed or added or changed or conflicts)
    return {'schema': 'abi-delta/v1', 'scope': 'supported-function-interfaces-only',
            'status': 'review-required' if review else 'no-function-differences',
            'before_count': len(old), 'after_count': len(new),
            'removed': [{'signature': s, **old[s]} for s in removed],
            'added': [{'signature': s, **new[s]} for s in added],
            'changed': changed, 'unchanged': unchanged, 'selector_conflicts': conflicts,
            'ignored_entry_counts': {'before': len(before) - len(old), 'after': len(after) - len(new)}}


def demo():
    # A hypothetical change to an ERC-20-style interface; no deployed ABI claim.
    before = [{'type': 'function', 'name': 'balanceOf', 'stateMutability': 'view',
               'inputs': [{'type': 'address'}], 'outputs': [{'type': 'uint256'}]}]
    after = json.loads(json.dumps(before))
    after[0]['outputs'] = [{'type': 'uint128'}]
    return compare(before, after)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', help='workspace-contained JSON ABI')
    parser.add_argument('--after', help='workspace-contained JSON ABI')
    parser.add_argument('--demo', action='store_true')
    args = parser.parse_args()
    if args.demo and (args.before or args.after):
        parser.error('--demo cannot be combined with ABI paths')
    if not args.demo and (not args.before or not args.after):
        parser.error('provide --before and --after, or --demo')
    try:
        result = demo() if args.demo else compare(inventory.read_abi(args.before), inventory.read_abi(args.after))
    except (ValueError, OSError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 1 if result['status'] == 'review-required' else 0


if __name__ == '__main__':
    raise SystemExit(main())
