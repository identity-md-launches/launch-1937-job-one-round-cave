# CSV Transitions

Explain which exact old values became which new values in selected columns
of two keyed CSV datasets. This offline Python 3.9+ standard-library tool helps
review bulk status migrations, labels or other repeated edits before opening
individual records. Keep the sibling `csv-reconcile/` folder: this tool imports
its unchanged bounded reader and comparison engine.

From the repository root, one command shows it working:

```sh
python3 -B line-2/tools/csv-transitions/transitions.py line-2/tools/csv-transitions/demo-before.csv line-2/tools/csv-transitions/demo-after.csv --key id --column status
```

When tried, it returned **1**, showing `pending` to `ready` for two rows and
`ready` to `done` for one row. The full comparison also reported one addition,
one removal, and four changed rows: the fourth change is in `owner`, which was
not selected. Exit **0** means the whole comparison is equal; **1** means any
difference or ambiguous key; **2** means invalid input/options. Errors emit no
partial report. The report is JSON on stdout; redirect it to a chosen file
inside your workspace if needed. No input file is modified.

Repeat `--key` for composite keys; repeat `--column` for several distinct
common non-key columns. Each selected column reports exact before/after value
pairs and their row counts, sorted by descending count, then literal before
and after strings. Column order follows the command. One changed row may
contribute to several columns. Unchanged values do not produce transitions.
No values are normalized: `01` differs from `1`, whitespace and case matter,
and an empty cell is a literal empty string.

Only keys present **exactly once on each side** contribute transitions.
Additions, removals, schema-only changes and duplicate-key groups never invent
value transitions. The report retains global schema, row summary, `equal`,
`complete`, and unpaired occurrence counts across *all* columns. A zero count
in the chosen column does not establish equality. `complete` means no duplicate
key ambiguity; it is not a claim that schemas match. Empty keys retain the
engine's literal semantics; observed uniqueness does not establish identity.
Key changes appear as a removal and addition. Use CSV Key Audit first when
identity or missing keys need review, and CSV Reconcile for individual records.

Reports include the selected data values and header names, but no key values,
record identities or paths. This is **not anonymization**. JSON escapes control
characters and Unicode for safe plain terminal output. Error diagnostics are
generic; argparse usage errors can echo supplied arguments.

Inputs must be workspace-local UTF-8 CSVs, with unique nonempty headers,
consistent row width, at most 16 MiB and 100,000 records per file. Selected
columns must exist in both headers and cannot be keys. The comparison and
source tables are held in memory. Inputs must remain stable throughout the
command: the engine compares them first, then the reader checks headers again;
these reads do not form an atomic snapshot. There is no network access,
installation, wallet, payment, fuzzy matching or write operation.

Checks:

```sh
python3 -B -m unittest discover -s line-2/tools/csv-transitions -v
```

All **10 behavioral tests passed**: aggregation and ordering, literal strings,
multiline/control cells, composite keys, multiple columns, duplicates,
additions/removals, unrelated edits and schema drift, invalid inputs, empty
cells/tables and CLI statuses. The unchanged engine's **17 tests passed** from
a byte-identical scratch copy. A self-comparison of the retained real historical
ZTO-first/IMD-second six-row observation CSV also returned 0 using
`chain_id,token_address,field` as the key and `raw_value` as the column. That
trial establishes offline equality only; it makes no fresh chain claim.
