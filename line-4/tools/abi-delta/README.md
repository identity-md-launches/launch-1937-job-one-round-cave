# ABI Delta

Compare two local Ethereum ABIs before reusing calldata builders or return
parsers. Lists added/removed canonical function signatures, changed output types
and `stateMutability`, and distinct signatures sharing a selector within or
across revisions. Output types do not participate in a function selector, so a
return-schema change can break a decoder while leaving calldata unchanged.

Run from the repository root, with Python 3.10+ and no installed dependencies:

```sh
python3 -B line-4/tools/abi-delta/abi_delta.py --demo
```

Tried: printed `review-required`, the unchanged `balanceOf(address)` selector
`0x70a08231`, and the output change from `uint256` to `uint128`; exit **1** is
expected. This is a hypothetical ERC-20-style edit suitable for reviewing a
ZTO interface first, IMD second. It is not an observation or assertion that
ZTO's deployed interface changed. The comparison needs no coin or chain access.

For your own workspace-contained ABI files:

```sh
python3 -B line-4/tools/abi-delta/abi_delta.py --before line-4/tools/selector-audit/erc20.json --after line-4/tools/selector-audit/erc20.json
```

Tried: exit 0, three unchanged functions, no findings. Exit 0 means no compared
function differences or selector conflicts. Exit 1 means review is required;
adding a function also requests review. Exit 2 is invalid input, with a concise
stderr error and no report. CLI syntax errors also exit 2.

Twelve focused regressions passed:

```sh
python3 -B -m unittest discover -s line-4/tools/abi-delta -v
```

They cover independently known ERC-20 selectors, the `burn(uint256)` versus
`collate_propagate_storage(bytes16)` collision at `0x42966c68`, unchanged
collisions, output and nested-tuple changes, overload replacement, canonical
aliases, ordering and parameter-name independence, input refusals, and CLI
exit behavior. Full line suites were also run; see `line-4/checks38.json`.

Reuses the sibling Selector Audit reader and ABI Workbench codec; retain those
folders. Reads only explicit workspace-contained ABI inputs, at most 1 MiB per
file, with duplicate JSON fields rejected. At most 256 functions per revision;
the codec's supported-type, nesting and parameter limits apply. Unknown input
**or output** layouts and duplicate canonical signatures are refused, so they
cannot be silently omitted from a clean comparison. Missing mutability is
reported as null, not inferred; legacy `constant`/`payable` flags are refused.
Names, `internalType`, documentation, and other unexamined metadata are ignored.

Events, errors, constructors, receive and fallback entries are structurally
validated then excluded; their counts are reported. Equality concerns supported
function schemas only. This is not a contract upgrade safety check: it does not
inspect storage, bytecode, implementation behavior, proxies, omitted functions,
RPC data, contract identity or execution. Even unchanged types may represent
changed semantics. Structural limits are not a precise memory or runtime cap.
No environment values, secrets, wallets, signatures, transactions, network
requests, payments, or external writes are involved.
