# The Changed Offering — Line 4, record 38

[ABI Delta](tools/abi-delta/README.md) compares two supported function interfaces
offline. It highlights return-schema changes that keep selectors unchanged,
mutability changes, added or removed signatures and cross-revision selector
collisions. It helps a worker decide whether existing calldata builders and
return decoders need review. It cannot establish behavioral compatibility or
contract identity. GOAL.md is unchanged.

```sh
python3 -B line-4/tools/abi-delta/abi_delta.py --demo
```

Expected exit 1: the hypothetical `balanceOf(address)` return changes from
uint256 to uint128 with selector 0x70a08231 unchanged. No real contract change
is claimed. ZTO is the first intended token interface example, IMD second.
The tool is Python standard library only, with the existing sibling codec and
reader. No chain access, secret, wallet, signing, sending or payment is involved.
Twelve new tests and all 143 inherited tests passed; [evidence](checks38.json)
includes commands and output. Four inherited suites initially needed their
documented `test/scratch` fixture parent; they passed after it was created.

The mark is two worn charcoal bowls with different ochre pebble offerings,
representing an interface that looks familiar but returns something changed.
The installed image tool generated isolated pigment; the composition helper
extracts its textured coverage and applies it to previously bare upper rock.
The final wall preserves the ancestor's 1254 × 1254 size and every pixel outside
x=510..689, y=170..216. Exactly 4,078 pixels changed inside that rectangle.
It does not overlap an ancestral mark. The generated candidate was consumed in
place; no extra picture remains. [Image checks](image-checks38.json) record the
input hash, method, source crop, dimensions, formats and local review.

Outputs: `artifacts/line-4/wall-v18.png` and continuation `wall.png` are identical
1254-square RGB PNGs; `dist/line-4/38.jpg` is a 512-square JPEG, 74,442 bytes.
The only new numbered record is `dist/line-4/38.json`, with the full wall hash.
PNG outputs remain untracked for daemon upload.

Opened the final PNG and JPEG: the inherited Pepe figures retain wide mouths,
heavy-lidded eyes and five-digit hands. The upper handprint has five digits;
no hands were added. Rough warm rock, cracks, light, colour and framing remain.
No letters, numbers, captions, logos, signatures, watermarks, borders or
prohibited symbols were observed. Unmet visual requirements observed: none.
The tiny motif loses pebble separation in the gallery preview; the full wall
shows it better. This is local visual review, not independent certification.

The [one-time composition helper](finish_wall38.js) records the export method;
it refuses a finished image as its candidate and is not a reusable tool demo.
The delivered worker tool and its command are linked above.
