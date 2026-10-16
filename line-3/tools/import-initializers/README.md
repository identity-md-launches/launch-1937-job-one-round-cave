# Import Initializers

Show the local `__init__.py` source files an explicit Python import could pass
through, without running the inspected project. For `import pkg.nested.worker`,
the ordinary explicit graph points at `worker`; this report also lists
`pkg/__init__.py` and `pkg/nested/__init__.py`, outermost first. These files can
contain important initialization code a worker would otherwise overlook.

From the repository root, run this offline command with Python 3.9 or newer:

```sh
python3 -B line-3/tools/import-initializers/initializers.py line-3/tools/import-initializers/examples
```

The command exited 0 when tried. It reported five import sites and two distinct
base initializer sources, including the two enclosing packages for
`pkg.nested.worker`. The example's top-level `raise RuntimeError(...)` did not
run. `from pkg import nested` separately shows a conditional child candidate:
a runtime package attribute can prevent a from-list child import.

Use `--json` for the complete report, source-byte SHA-256 manifest, collection
counts and limits. Each site retains its module, relative source path, line,
AST column (a UTF-8 byte offset), alias index, spelling, ordered traversal steps,
and initializer paths. The inherited Import Map and its explicit graph are
unchanged. Only the delivered Import Budget/Import Map helpers are loaded;
inspected source is parsed as bytes with `ast.parse`, never imported.

Interpretation:

- `regular_package` contributes its selected `__init__.py` source.
- `namespace_candidate` has local descendants but no initializer of its own.
- `source_module` terminates a valid source path; it blocks traversal to a
  further dotted descendant. This is recorded as `blocked_by_source_module`.
- `missing_source` means absent from this collected Python-source snapshot. It
  may be an external, standard-library or extension module; it is not proof of
  an import error. Earlier package candidates remain visible on a missing path.
- Relative anchors use the importing source's package. An anchor that escapes
  the import root is `unresolved_relative`.
- A `child_candidate` describes an exact local child source of a package used
  by `from ... import ...`. Its `only_if_attribute_missing` condition is never
  evaluated. A wildcard does not expand children. Namespace children without
  their own `.py` or `__init__.py` are not listed as from-list child candidates.

A regular package wins over a same-named `.py` file, matching Import Map's
selection; the collision and both source paths remain visible. Shadowed files
are collected and hashed but not parsed. Parse failures are reported and can
hide import sites. The explicit root is an import search root; a root-level
`__init__.py` is admitted to the manifest but has no inferred package name and
is not parsed, matching the mapper.

This is a review aid, not an initialization trace or execution order. It does
not evaluate conditions, runtime bindings, `sys.modules`, search-path changes,
custom loaders or initializer side effects. An initializer already in progress
or cached may not run again. Initializers' own imports appear as separate
sites, without recursive simulation. Dynamic calls are handled separately by
[Import Dynamic](../import-dynamic/README.md). Runtime success and safety cannot
be established by these candidates.

Collection reuses [Import Budget](../import-budget/README.md): workspace-only
roots, skipped symlinks/hidden/dependency directories, regular Python files,
and refusal before analysis when an input budget is exceeded. Defaults are
1,000 files, 262,144 bytes per file, 8,388,608 source bytes total, 20,000 directory
entries and depth 64. Set `--max-files`, `--max-file-bytes`, `--max-total-bytes`,
`--max-entries` and `--max-depth` explicitly as needed. These are input limits,
not CPU, memory or time guarantees. Keep the source tree stable during a scan.

Exit 0 means analysis completed; `--strict` exits 1 on parse issues or source
collisions. Collection failures and invalid limits exit 2 with a structured
refusal and no partial result. Missing source alone is not a strict failure.

The real `shared/import-drift` worker was also inspected as source only:
30 files, 147,941 bytes, 224 explicit import sites, zero parse/collision issues,
and no package initializer candidates. Its flat source layout explains the
zero result; it is not evidence that runtime initialization cannot occur.
[observed-source.json](observed-source.json) retains that snapshot's manifest
and report. No chain, token, installation or network is needed.

Fourteen behavioral checks cover nested/relative imports, namespace packages,
conditional child candidates, module blockers, missing sources, collisions,
encodings/parse errors, repeated same-line aliases, ignored root initializers,
nested conditions, execution traps, manifests and refusal/strict exits:

```sh
python3 -B -m unittest discover -s line-3/tools/import-initializers -v
```
