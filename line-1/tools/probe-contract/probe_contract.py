#!/usr/bin/env python3
"""Capture bounded HTTP observations with explicit expectations; compare offline."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys

TOOLS = Path(__file__).resolve().parent.parent


def module(name, relative):
    path = TOOLS / relative
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


sentry = module('contract_sentry', 'endpoint-sentry/sentry.py')
watchdog = module('contract_watchdog', 'deadline-sentry/deadline_sentry.py')
delta = module('contract_delta', 'report-delta/report_delta.py')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def validate_spec(s):
    keys = {'url', 'timeout_seconds', 'deadline_seconds', 'max_bytes',
            'max_redirects', 'status', 'json', 'path', 'compare_value', 'value',
            'producer_sha256'}
    if not isinstance(s, dict) or set(s) != keys:
        raise ValueError('missing or unknown contract fields')
    if not isinstance(s['url'], str):
        raise ValueError('URL must be a string')
    sentry.https_url(s['url'])
    for key in ('timeout_seconds', 'deadline_seconds'):
        if type(s[key]) not in (int, float) or not math.isfinite(s[key]) or not 0 < s[key] <= 120:
            raise ValueError('invalid ' + key)
    for key, low, high in [('max_bytes', 1, 16777216), ('max_redirects', 0, 10), ('status', 100, 599)]:
        if type(s[key]) is not int or not low <= s[key] <= high:
            raise ValueError('invalid ' + key)
    if type(s['json']) is not bool or type(s['compare_value']) is not bool:
        raise ValueError('expectation switches must be booleans')
    path = s['path']
    if path is not None:
        if not isinstance(path, str) or (path and not path.startswith('/')):
            raise ValueError('invalid JSON pointer')
        for token in path.split('/')[1:]:
            sentry.pointer({token.replace('~1', '/').replace('~0', '~'): None}, '/' + token)
    if s['compare_value'] and path is None:
        raise ValueError('value check needs a pointer')
    if not s['compare_value'] and s['value'] is not None:
        raise ValueError('unused expected value')
    hashes = s['producer_sha256']
    if not isinstance(hashes, dict) or set(hashes) != {'endpoint', 'watchdog', 'contract'}:
        raise ValueError('missing producer hashes')
    if any(not isinstance(h, str) or not re.fullmatch('[0-9a-f]{64}', h) for h in hashes.values()):
        raise ValueError('invalid producer hash')
    canonical(s)
    return s


def make_spec(args):
    files = {'endpoint': TOOLS / 'endpoint-sentry/sentry.py',
             'watchdog': TOOLS / 'deadline-sentry/deadline_sentry.py',
             'contract': Path(__file__).resolve()}
    return validate_spec(dict(url=args.url, timeout_seconds=args.timeout,
        deadline_seconds=args.deadline, max_bytes=args.max_bytes,
        max_redirects=args.max_redirects, status=args.status, json=args.json,
        path=args.expect_path, compare_value=args.expect_value is not None,
        value=delta.strict_json(args.expect_value) if args.expect_value is not None else None,
        producer_sha256={k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in files.items()}))


def capture(s, supervisor=None):
    validate_spec(s)
    command = [sys.executable, '-I', '-B', str(TOOLS / 'endpoint-sentry/sentry.py'),
               s['url'], '--timeout', str(s['timeout_seconds']),
               '--max-bytes', str(s['max_bytes']), '--max-redirects', str(s['max_redirects']),
               '--status', str(s['status'])]
    if s['json']:
        command.append('--json')
    # '=' prevents a pointer or JSON string beginning '-' becoming an option.
    if s['path'] is not None:
        command.append('--expect-path=' + s['path'])
    if s['compare_value']:
        command.append('--expect-value=' + canonical(s['value']))
    result, code = (supervisor or watchdog.supervise)(command, s['deadline_seconds'])
    return {'schema': 'probe-contract/v1', 'contract': s, 'observation': result}, code


def admitted(report):
    if not isinstance(report, dict) or set(report) != {'schema', 'contract', 'observation'} or report['schema'] != 'probe-contract/v1':
        raise ValueError('expected probe-contract/v1 capture')
    s = validate_spec(report['contract'])
    wrapper = report['observation']
    if not isinstance(wrapper, dict) or type(wrapper.get('ok')) is not bool:
        raise ValueError('invalid observation wrapper')
    if 'probe' not in wrapper:
        if wrapper['ok'] or not isinstance(wrapper.get('error'), dict) or not isinstance(wrapper['error'].get('kind'), str):
            raise ValueError('invalid incomplete observation')
        return s, None
    p = wrapper['probe']
    evidence = delta.observation(p)
    if wrapper['ok'] is not evidence['ok']:
        raise ValueError('wrapper contradicts probe')
    if evidence['url'] != s['url'] or evidence['limits'] != {
        'timeout_seconds': s['timeout_seconds'], 'max_bytes': s['max_bytes'],
        'max_redirects': s['max_redirects']}:
        raise ValueError('probe contradicts contract URL or limits')
    expected = ['status']
    if s['json'] or s['path'] is not None:
        expected.append('json')
    if s['path'] is not None:
        expected.append('json_pointer')
    if s['compare_value']:
        expected.append('json_value')
    names = [c['name'] for c in evidence['checks']]
    if names != expected[:len(names)] or (evidence['error_kind'] is None and names != expected):
        raise ValueError('probe contradicts contract check sequence')
    for c in evidence['checks']:
        if c['name'] == 'status' and c.get('expected') != s['status']:
            raise ValueError('probe contradicts expected status')
        if c['name'] in {'json_pointer', 'json_value'} and c.get('path') != s['path']:
            raise ValueError('probe contradicts expected pointer')
    return s, p


def compare(before, after):
    a, pa = admitted(before)
    b, pb = admitted(after)
    changed = [k for k in sorted(a) if canonical(a[k]) != canonical(b[k])]
    reasons = []
    if changed:
        reasons.append('contracts differ')
    if pa is None or pb is None:
        reasons.append('incomplete worker observation')
    if reasons:
        return {'schema': 'probe-contract-comparison/v1', 'verdict': 'inconclusive',
                'reasons': reasons, 'changed_contract_fields': changed}
    result = delta.compare(pa, pb, same_expectations=True)
    result.update(schema='probe-contract-comparison/v1', changed_contract_fields=[])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest='mode', required=True)
    p = sub.add_parser('capture', allow_abbrev=False)
    p.add_argument('url')
    p.add_argument('--timeout', type=float, default=5)
    p.add_argument('--deadline', type=float, default=8)
    p.add_argument('--max-bytes', type=int, default=262144)
    p.add_argument('--max-redirects', type=int, default=0)
    p.add_argument('--status', type=int, default=200)
    p.add_argument('--json', action='store_true')
    p.add_argument('--expect-path')
    p.add_argument('--expect-value')
    p = sub.add_parser('compare', allow_abbrev=False)
    p.add_argument('before')
    p.add_argument('after')
    args = parser.parse_args(argv)
    try:
        if args.mode == 'capture':
            result, code = capture(make_spec(args))
        else:
            result = compare(delta.load(args.before), delta.load(args.after))
            code = 2 if result['verdict'] == 'inconclusive' else int(not result['after_ok'])
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError) as error:
        print(json.dumps({'schema': 'probe-contract-error/v1', 'error': str(error)}))
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return code


if __name__ == '__main__':
    sys.exit(main())
