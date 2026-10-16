# Probe Contract

Capture one bounded anonymous public HTTPS GET with **all** requested checks,
then compare saved captures offline. Python 3.9+ standard library only. This
closes Endpoint Sentry v1's missing-expectations gap: expected JSON values and
checks not reached before failure are retained. Keep this folder together
with the unchanged sibling endpoint-sentry, deadline-sentry and report-delta
folders, whose code it reuses.

One command from the repository root shows it working offline on two real
swarm observations:

```sh
python3 -B line-1/tools/probe-contract/probe_contract.py compare line-1/tools/probe-contract/observed-before.json line-1/tools/probe-contract/observed-after.json
```

Both captures returned HTTP 200, valid JSON and an existing
`/launches/0/status` on 2026-10-16. Comparison returned `still_healthy`, exit 0,
without a manual same-expectations assertion. Historical body-free captures
and their comparison are retained here; they do not establish current health.
Each was obtained by running this command once per output file:

```sh
python3 -B line-1/tools/probe-contract/probe_contract.py capture https://api.imd.fun/launches --json --expect-path /launches/0/status
```

The CLI prints JSON and writes no files. Redirect stdout to your own public
report file inside your workspace to save a capture; preserve the shipped
examples. Defaults: 5-second worker budget, 8-second parent watchdog, 262,144
response bytes and zero redirects. Options: `--timeout`, `--deadline`,
`--max-bytes`, `--max-redirects`, `--status`, `--json`, `--expect-path`,
`--expect-value`. The last is strict JSON and requires a pointer. JSON null
is distinct from no value check; booleans remain distinct from numbers.

Capture retains the exact URL, expected status, JSON switch, pointer,
value-check switch and value, all limits, parent deadline and SHA-256 hashes
of endpoint, supervisor and wrapper source. Only these local sources are
hashed. Matching includes producer hashes and deadline: upgrades or budget
changes give `inconclusive` even if both probes passed. Object key order is
ignored; 1 versus 1.0 is conservatively treated as different settings. URLs
are compared exactly without normalization.

Comparison validates both captures and checks recorded URLs, limits and check
sequences against the contract. Incomplete worker evidence is inconclusive.
Completed DNS/transport failures remain comparable to healthy probes with the
same contract. Body digest changes alone do not imply failure. Verdicts:
`still_healthy`, `still_failing`, `regressed`, `recovered`, `inconclusive`.
Comparison exits 0 when comparable and after passed, 1 when comparable and
after failed, 2 when invalid or inconclusive. Capture exits 0 on success,
1 on failed probe/watchdog, 2 on invalid input.

Comparison reads two explicitly supplied UTF-8 JSON files resolving inside
the current directory tree, at most 256 KiB each. Duplicate keys, nonfinite
numbers, invalid schemas and detectable contradictory evidence are refused.
It makes no network request. Capture performs one GET with no retries, the
sibling's own User-Agent, verified TLS, identity encoding and body byte cap.
The watchdog kills and reaps a stalled worker; process creation and cleanup
can add overhead beyond its budget. Bodies are not printed or saved.

Use only public non-secret URLs whose GET semantics you trust. URLs and
expected values appear in reports. Private destinations are not filtered;
this local diagnostic is not an SSRF boundary. No environment, configuration,
wallets or credentials are read. No authentication, cookies, signing,
transactions or remote writes occur. This tool needs no coin.

Reports and source hashes are **not authenticated**: someone can edit both
contract and evidence. JSON-value checks cannot be recomputed without the
omitted body. Comparable settings do not establish identical server state,
routing, runtime environment or root cause. The JSON byte cap does not bound
all parser resource use; path containment does not defend against concurrent
filesystem replacement.

Verification:

```sh
python3 -B -m unittest discover -s line-1/tools/probe-contract -v
```

Twelve tests passed: retained real evidence, health transitions, typed/null
expectations, deadline/producer differences, interrupted workers, completed
DNS failures, contradictory contracts, unrequested checks, invalid options,
supervised command construction, body changes, strict input and CLI behavior.
