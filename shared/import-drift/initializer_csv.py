#!/usr/bin/env python3
"""Review source-linked package initializer candidates as exact keyed CSV."""
import argparse
import csv
import io
import json
import sys

import budget
import initializers
import import_map
import reconcile
import transitions

KEYS = ('path', 'line', 'column', 'alias_index')
COLUMNS = KEYS + ('module', 'spelling', 'base_status', 'base_evidence',
                  'conditional_evidence', 'source_sha256')
SCOPE = ('Static source candidates only, not observed imports or execution order. '
         'Keys are source coordinates, not semantic identities across edits. '
         'Line shifts appear as removals/additions. Missing source can mean an '
         'external import; it does not establish a missing installation. '
         'Equality of CSV rows does not certify complete or safe source. '
         'Keep snapshot stderr evidence and inspect its issues and manifest.')


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'))


def snapshot(root, limits=None):
    limits = dict(budget.DEFAULTS if limits is None else limits)
    sources, inventory = budget.collect(root, limits, import_map.SKIP_DIRS)
    result = initializers.inspect_sources(sources, import_map)
    hashes = {item['path']: item['sha256'] for item in inventory['manifest']}

    def linked(value):
        if value is None:
            return None
        # Keep complete traversal/collision evidence and attach exact source hashes.
        value = json.loads(canonical(value))
        paths = {p for step in value['steps'] for p in step['source_paths']}
        value['source_sha256'] = {path: hashes[path] for path in sorted(paths)}
        return value

    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator='\n')
    writer.writeheader()
    for site in result['sites']:
        writer.writerow({**{key: site[key] for key in KEYS},
                         'module': site['module'], 'spelling': site['spelling'],
                         'base_status': site['base']['status'],
                         'base_evidence': canonical(linked(site['base'])),
                         'conditional_evidence': canonical(linked(site['child_candidate'])),
                         'source_sha256': hashes[site['path']]})
    evidence = dict(result, schema='initializer-csv/v1', status='complete',
                    inventory=inventory, limits=limits, scope=SCOPE,
                    analysis_scope=initializers.SCOPE, collection_scope=budget.SCOPE)
    return stream.getvalue(), evidence


def compare(before, after):
    for path in (before, after):
        columns, groups, _ = reconcile.load_table(path, KEYS)
        if columns != list(COLUMNS):
            raise ValueError('expected initializer-csv/v1 columns')
        for key, rows in groups.items():
            if not key[0] or len(rows) != 1:
                raise ValueError('source coordinate keys must be unique and nonempty')
            for number, minimum in zip(key[1:], (1, 0, 0)):
                if not number.isascii() or not number.isdecimal() or str(int(number)) != number or int(number) < minimum:
                    raise ValueError('invalid source coordinate')
    # Inputs must stay stable across these bounded reads, as in CSV Transitions.
    details = reconcile.reconcile(before, after, KEYS)
    counts = transitions.transitions(before, after, KEYS, ['base_status'])
    return {'schema': 'initializer-review/v1', 'comparison': details,
            'status_transitions': counts, 'scope': SCOPE}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    snap = commands.add_parser('snapshot')
    snap.add_argument('root')
    for name, default in budget.DEFAULTS.items():
        snap.add_argument('--max-' + name.replace('_', '-'), dest=name, type=int, default=default)
    diff = commands.add_parser('compare')
    diff.add_argument('before')
    diff.add_argument('after')
    args = parser.parse_args(argv)
    try:
        if args.command == 'snapshot':
            text, evidence = snapshot(args.root, {k: getattr(args, k) for k in budget.DEFAULTS})
            print(canonical(evidence), file=sys.stderr)
            sys.stdout.write(text)
            return int(bool(evidence['issues']))
        result = compare(args.before, args.after)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return int(not result['comparison']['equal'])
    except (OSError, ValueError, RuntimeError, RecursionError) as error:
        print(canonical({'schema': 'initializer-csv/v1', 'status': 'refused',
                         'error': str(error)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
