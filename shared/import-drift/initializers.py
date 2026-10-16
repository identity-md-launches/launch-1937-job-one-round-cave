#!/usr/bin/env python3
"""List source candidates for package initialization without executing inspected code."""
import argparse
import ast
import importlib.util
import json
from pathlib import Path
import sys

SCOPE = ('Source candidates, not runtime execution: the explicit root is an import root, '
         'not itself a package. Regular package __init__.py files are listed outermost '
         'first; namespace directories contribute no initializer. A source module blocks '
         'a dotted traversal beyond itself. From-import child candidates are conditional '
         'because an attribute may already exist. Conditions, aliases, sys.modules, '
         'search paths, loaders, extension modules and runtime package attributes are '
         'not evaluated. Initializer imports are inspected as separate sites, not '
         'recursively executed. Dynamic imports and wildcard expansion are omitted. '
         'No project code is imported; the existing explicit import graph is unchanged.')


def load_budget():
    path = Path(__file__).resolve().with_name('budget.py')
    spec = importlib.util.spec_from_file_location('line3_initializers_budget', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def catalog_sources(sources, mapper):
    catalog = {}
    for path in sorted(sources):
        name = mapper.module_name(Path(path))
        if name:
            catalog.setdefault(name, []).append(path)
    return catalog


def walk_target(target, catalog):
    """Describe one dotted source path, stopping before impossible descendants."""
    steps, initializers = [], []
    if not target:
        return {'target': target, 'status': 'unresolved_relative',
                'steps': steps, 'initializers': initializers}
    parts = target.split('.')
    namespaces = {'.'.join(name.split('.')[:i]) for name in catalog
                  for i in range(1, len(name.split('.')))}
    status = 'source_candidate'
    for i in range(1, len(parts) + 1):
        name = '.'.join(parts[:i])
        paths = catalog.get(name, [])
        packages = [p for p in paths if Path(p).name == '__init__.py']
        if packages:
            selected = min(packages)
            kind = 'regular_package'
            initializers.append({'module': name, 'path': selected})
        elif paths:
            selected, kind = min(paths), 'source_module'
        else:
            selected = None
            kind = 'namespace_candidate' if name in namespaces else 'missing_source'
        steps.append({'module': name, 'kind': kind, 'selected': selected,
                      'source_paths': sorted(paths)})
        if kind == 'missing_source':
            status = 'missing_source'
            break
        if kind == 'source_module' and i < len(parts):
            status = 'blocked_by_source_module'
            break
    return {'target': target, 'status': status, 'steps': steps,
            'initializers': initializers}


def inspect_sources(sources, mapper):
    catalog = catalog_sources(sources, mapper)
    sites, issues = [], []
    # Match Import Map's regular-package preference; do not parse shadowed files.
    for module, paths in sorted(catalog.items()):
        path = min(paths, key=lambda p: (Path(p).name != '__init__.py', p))
        if len(paths) > 1:
            issues.append({'type': 'module_collision', 'module': module,
                           'path': path, 'source_paths': sorted(paths)})
        try:
            tree = ast.parse(sources[path], filename=path)
        except (SyntaxError, UnicodeError, ValueError) as exc:
            issues.append({'type': 'parse_error', 'path': path,
                           'line': getattr(exc, 'lineno', None), 'detail': str(exc)})
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(node, ast.Import):
                requests = [(alias.name, alias.name, False) for alias in node.names]
            else:
                anchor = (mapper.relative_anchor(module, Path(path).name == '__init__.py',
                                                node.level, node.module)
                          if node.level else node.module)
                spelling = '.' * node.level + (node.module or '')
                requests = [(spelling + ' import ' + alias.name, anchor, True)
                            for alias in node.names]
            for index, (spelling, target, from_import) in enumerate(requests):
                base = walk_target(target, catalog)
                item = {'module': module, 'path': path, 'line': node.lineno,
                        'column': node.col_offset, 'alias_index': index,
                        'spelling': spelling, 'base': base, 'child_candidate': None}
                # Python may try a child module only for a package from-list.
                # A matching attribute can suppress that attempt, so never make an edge.
                if from_import and base['status'] == 'source_candidate' and base['steps']:
                    alias = node.names[index].name
                    last = base['steps'][-1]['kind']
                    child = target + '.' + alias
                    if alias != '*' and last in ('regular_package', 'namespace_candidate') and child in catalog:
                        item['child_candidate'] = dict(walk_target(child, catalog),
                                                      condition='only_if_attribute_missing')
                sites.append(item)
    sites.sort(key=lambda s: (s['path'], s['line'], s['column'], s['alias_index']))
    issues.sort(key=lambda s: (s['path'], s.get('line') or 0, s['type']))
    unique = {(p['module'], p['path']) for s in sites for p in s['base']['initializers']}
    conditional = {(p['module'], p['path']) for s in sites if s['child_candidate']
                   for p in s['child_candidate']['initializers']}
    return {'sites': sites, 'issues': issues,
            'summary': {'import_sites': len(sites), 'issues': len(issues),
                        'base_initializer_sources': len(unique),
                        'additional_conditional_initializer_sources': len(conditional - unique)}}


def analyze(root, limits=None):
    budget = load_budget()
    mapper = budget.load_mapper()
    limits = dict(budget.DEFAULTS if limits is None else limits)
    sources, inventory = budget.collect(root, limits, mapper.SKIP_DIRS)
    return dict(inspect_sources(sources, mapper), status='complete', limits=limits,
                inventory=inventory, scope=SCOPE, collection_scope=budget.SCOPE)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--strict', action='store_true', help='exit 1 on parse issues or collisions')
    budget = load_budget()
    for name, default in budget.DEFAULTS.items():
        parser.add_argument('--max-' + name.replace('_', '-'), dest=name, type=int, default=default)
    args = parser.parse_args(argv)
    try:
        result = analyze(args.root, {name: getattr(args, name) for name in budget.DEFAULTS})
    except (OSError, ValueError, RuntimeError, RecursionError) as exc:
        print(json.dumps({'status': 'refused', 'error': getattr(exc, 'evidence',
                         {'type': 'scan_error', 'detail': str(exc)})}, indent=2))
        return 2
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for site in result['sites']:
            base = site['base']
            paths = ', '.join(p['path'] for p in base['initializers']) or '(none)'
            print(f"{site['path']}:{site['line']}:{site['column']} {site['spelling']} — "
                  f"{base['status']}; initializer candidates: {paths}")
            if site['child_candidate']:
                paths = ', '.join(p['path'] for p in site['child_candidate']['initializers']) or '(none)'
                print('  if attribute missing: ' + paths)
        for issue in result['issues']:
            print('Issue: ' + json.dumps(issue))
        print(json.dumps(result['summary'], sort_keys=True))
        print(SCOPE)
    return int(bool(args.strict and result['issues']))


if __name__ == '__main__':
    sys.exit(main())
