# Initializer CSV Review

Review changes in Python package-initialization **source candidates** between
source revisions without running the inspected project. This joins Line 3's
Import Initializers to Line 2's exact CSV Reconcile and CSV Transitions.
Python 3.10+ standard library only; keep this shared folder together.

From the repository root, one command works offline on a retained real worker
snapshot:

```sh
python3 -B shared/import-drift/initializer_csv.py compare shared/import-drift/observed-initializers38.csv shared/import-drift/observed-initializers38.csv
```

Tried: exit 0, 257 unchanged import-site rows, no status transitions. This
self-comparison demonstrates reproducibility, not equality between revisions.
The source-only scan of this shared worker admitted 34 files, with no parse
issues or module collisions and no package initializer candidates. The worker
uses a flat module layout. The complete source manifest, limits and warnings
are in [the retained evidence](../../gathering/initializer-evidence38.json).
Behavioral tests separately exercise real package-source changes and status
transitions, with execution traps that must never run.

To inspect your own source revisions, take two snapshots into different local
files and compare them. Snapshot prints CSV to stdout and complete JSON evidence
to stderr. Preserve both, for example:

```sh
python3 -B shared/import-drift/initializer_csv.py snapshot shared/import-drift
```

Use shell redirection to your chosen workspace CSV and evidence JSON paths;
keep the shipped examples intact. Repeat after your source change, then run
`initializer_csv.py compare BEFORE.csv AFTER.csv`. It emits the full keyed
comparison and aggregate exact `base_status` transitions. A candidate initializer
content change is visible through its SHA-256 even when status is unchanged.
Conditional from-list child candidates remain conditional and retain their
complete chains and source hashes. Module/package collisions retain every
candidate path in the evidence; the analyzer's regular-package preference does
not resolve runtime ambiguity.

The fixed key is `(path, line, column, alias_index)`. Paths are relative to the
explicit import root; lines start at 1 and columns are AST UTF-8 byte offsets
starting at 0. Multiple aliases and semicolon-separated imports remain distinct.
These are location keys, **not semantic import identities**: inserted lines can
appear as removals/additions. Counts cannot establish unchanged behavior. Each
row carries the importing file's byte hash, spelling, module, status and linked
base/conditional evidence. An edit elsewhere in that importing file also changes
its hash. Missing local source can be a standard-library or installed external
module, and never establishes a missing installation.

Snapshot exit 0 means completed with no recorded parse/collision issues; exit 1
means completed CSV with issues that must be reviewed in stderr; exit 2 means
refusal with **no CSV**. Compare exits 0 for equal CSV values, 1 for differences,
and 2 for invalid inputs. CSV equality never certifies source completeness:
parse errors, skipped files and files without import sites live in the retained
snapshot evidence. The CSV validator checks columns, unique coordinates and
coordinate syntax; it does not authenticate claims or independently validate
all JSON evidence cells. No signature or trusted provenance is implied.

Source admission uses the existing bounded collector: defaults are 1,000 files,
262,144 bytes per file, 8 MiB total source, 20,000 directory entries and depth 64.
Override via `--max-files`, `--max-file-bytes`, `--max-total-bytes`, `--max-entries`
and `--max-depth`. Symlinks, dependency/hidden directories and nonregular files
are skipped. Compare CSVs inherit the 16 MiB/100,000-record parser limits.
Sources and CSVs must remain stable during reads: comparison validates and reads
the files several times, without an atomic filesystem snapshot. Tables, ASTs
and reports are held in memory; input budgets are not runtime or memory limits.

An explicit source root is treated as an import root, not a package. Dynamic
imports, package attributes, search-path modifications, loaders, cached modules
and conditional execution are not evaluated. The explicit import graph stays
unchanged. This is reading guidance and review evidence, not execution order,
upgrade safety, dependency installation advice or safe parallelism. No network,
coin, credentials, environment inspection or transactions are needed.

```sh
python3 -B -m unittest discover -s shared/import-drift -p test_initializer_csv.py -v
```

Seven tests passed: initializer byte changes, missing-to-present transitions,
conditional children/namespaces, coordinate shifts/multiple aliases/empty roots,
key/schema refusals, budget refusal without partial CSV, and preserved collision
warnings even when a snapshot compares equal to itself.
