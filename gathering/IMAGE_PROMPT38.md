# The Careful Handoff — Gathering 38

Built-in imagegen edited the verified Gathering 37 wall, whose SHA-256 is
`0f4d55a16bccf29be5f82d92892c7cb062a9be4f9c3836c6f0619a7eff67fad8`.
The earlier `wall.png` continuation was absent, so the latest available full
wall `artifacts/gathering/wall-v17.png` was used and checked against record 37.

Final prompt:

> Use case: precise-object-edit. This is an existing prehistoric cave painting,
> edit target. Preserve the entire 1254 by 1254 square wall EXACTLY: all ancestor
> pigments, Pepe the frog with heavy-lidded eyes, wide mouth and five-digit hands,
> every existing figure, every crack and rock texture, torchlight, colors,
> framing. Add ONLY one small worn earth-pigment motif in the empty bottom-center
> rock patch, approximately x=480..710 y=1115..1200: two small ochre cups joined
> by a thin charcoal trail, with three tiny chalk-white pebbles on the trail,
> symbolizing careful handoff of evidence between workers. Keep it small and
> subtle and hand-drawn with uneven worn strokes so bare stone shows through.
> Do not cover any previous mark. NO new hands or figures. NO letters, numbers,
> writing, caption, signature, logos, watermark, border or frame. Do not clean,
> remove, move, replace or redraw anything already present. Same original image
> dimensions.

The generated addition landed slightly farther right than the requested patch.
It was not moved. The one-time export [finish_wall38.js](finish_wall38.js)
transferred only reviewed pigment-colored changes and their soft edges in the
previously bare rectangle x=485..760, y=1100..1165. It retained the exact ancestor
pixels everywhere else. The source tool's broader texture repaint was discarded.
The export verifies the exact ancestor hash and refuses a different input.

The finished [wall-v18.png](../artifacts/gathering/wall-v18.png) and `wall.png`
are identical **1254 × 1254 RGB PNGs**. [38.jpg](../dist/gathering/38.jpg) is
**512 × 512 JPEG**, 68,004 bytes. Exactly **7,485 pixels** changed; all are in
the reviewed patch, with zero changes outside. The record's artifact URL is
the SHA-256 of the full PNG. The two PNG outputs remain untracked for upload.

Review step chosen: opened the ancestor, generated candidate, final full PNG
and final JPEG. The new motif is two ochre cups and three chalk stones joined
by a charcoal curve, all in earth pigments with rough stone showing through.
The inherited Pepe retains his heavy-lidded eyes, broad mouth and hands with
four fingers plus one thumb each. No new hand or handprint was added. The
inherited small upper hand-like motif is unchanged pixel for pixel. The earlier
marks, cracks, light, warm rock and square framing are retained. No letters,
numbers, signatures, logos, watermarks, borders or prohibited symbols observed.
**Unmet visual requirements observed: none.** The cups and pebbles are subtle
at 512 px and nearly disappear in the tiny embedded gallery previews. This is
local visual review, not independent visual certification.
