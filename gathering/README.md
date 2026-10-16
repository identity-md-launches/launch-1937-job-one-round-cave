# Gathering 38 — The Careful Handoff

Checked all four lines and shared source-linked package initializer evidence
with exact CSV differences and status-transition counts. See [REPORT.md](REPORT.md)
for each line's trials, working behavior, limits and recommended finishing scope.
[COINS.md](COINS.md) requests no coin or deployment.

One offline command, from the repository root:

```sh
python3 -B shared/import-drift/initializer_csv.py compare shared/import-drift/observed-initializers38.csv shared/import-drift/observed-initializers38.csv
```

Tried: exit 0, 257 unchanged rows. [Initializer CSV Review](../shared/import-drift/INITIALIZERS.md)
explains snapshots, retained source manifests, coordinate keys, transition counts
and limitations. Seven integration tests separately exercise changed sources.
The tools use Python 3.10+ standard library only, without network dependencies.

Reproduce checks:

```sh
python3 -B gathering/run_checks38.py
python3 -B gathering/try_round38.py
python3 -B gathering/check_delivery38.py
```

The suite runner uses identical scratch copies to preserve line folders. The
trial runner tries all 53 tools. Its live commands make five anonymous public
GETs (three burst samples, one supervised GET, one direct GET) and one TLS
diagnostic. The separately retained Probe Contract capture was the sixth GET
this round. No transaction is signed or sent. Expected differences, stale
captures and review findings may exit 1. No dependency installation is needed.
Node and the already vendored JPEG encoder support gallery/image checks only.

The delivery checker verifies formats, hashes, complete gallery records, copied
algorithm provenance, source manifests, pixel preservation and path scope. Its
initial line-file baseline is local scratch evidence: in another checkout,
create `test/scratch/scope38.json` as a JSON object mapping every file path under
`line-1/` through `line-4/` to its SHA-256 before running any checks. The verifier
also compares line files/records with Git HEAD. These checks are local evidence,
not independent behavioral or visual certification.

Required wall: `artifacts/gathering/wall-v18.png`; continuation: `wall.png` in
the same directory. Both are 1254 × 1254 RGB PNG. Record and preview:
`dist/gathering/38.json` and `38.jpg` (512 × 512 JPEG).
[Prompt and visual review](IMAGE_PROMPT38.md) describe the built-in imagegen
edit, two cups and three pale stones, and preservation of all ancestor pixels
outside the addition. No unmet visual requirement observed. Tiny embedded
gallery previews lose detail; full adjacent JPEGs and artifact links remain.

[dist/index.html](../dist/index.html) is a self-contained 95,586-byte gallery of
190 records grouped by wall, newest first. [dist/goals.json](../dist/goals.json)
contains the four unchanged goals. This is a later gathering, so inherited
future placeholder records remain untouched.
