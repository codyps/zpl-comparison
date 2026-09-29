# Canvas dimension audit: 2026-09-29

The complete saved comparison was checked: 133 accuracy, 598 conformance,
20 layout, 8 external, and 120 ZQ610 candidate observations for codyps/zpl.
Invalid-input probes and performance samples are not printer-canvas comparisons.
The separate paired-profile measurements are not duplicate candidate observations.

All 26 candidate canvas mismatches occur in the ZQ610 suite. The adapter used
the default ZD621 profile, whose `^PW` and `^LL` commands override initial
width/height options. The ZQ610 Plus firmware preview instead keeps the
configured height, rounds widths to 64 dots, caps widths at 384 dots, and
latches width after the first draw. These behaviors already exist in
`ZQ610_PLUS_203_DPI` in codyps/zpl; this is a comparison configuration fault.
The checked-in comparison source pin also predates that profile.

The fix selects the ZQ610 profile explicitly for this suite, updates the pin,
and retains default ZD621 behavior elsewhere. Source bytes, printer captures,
native origins, and scoring rules are unchanged. No padding or resizing is used.

| Case | Previous output | Printer canvas | Cause |
|---|---|---|---|
| canvas-height-120 | 384 × 120 | 384 × 2030 | fixed preview height |
| canvas-height-400 | 384 × 400 | 384 × 2030 | fixed preview height |
| canvas-width-120 | 120 × 2030 | 128 × 2030 | 64-dot width rounding |
| canvas-width-120-fit | 120 × 2030 | 128 × 2030 | 64-dot width rounding |
| canvas-width-300 | 300 × 2030 | 320 × 2030 | 64-dot width rounding |
| canvas-width-300-fit | 300 × 2030 | 320 × 2030 | 64-dot width rounding |
| canvas-width-400 | 400 × 2030 | 384 × 2030 | width cap |
| canvas-width-832 | 832 × 2030 | 384 × 2030 | width cap |
| smoke-aztec | 384 × 1218 | 384 × 2030 | fixed preview height |
| smoke-aztec_alias | 384 × 1218 | 384 × 2030 | fixed preview height |
| smoke-aztec_rune | 384 × 1218 | 384 × 2030 | fixed preview height |
| smoke-codabar | 384 × 1218 | 384 × 2030 | fixed preview height |
| width-boundary-1 | 1 × 200 | 64 × 2030 | fixed preview height, 64-dot width rounding |
| width-boundary-127 | 127 × 200 | 128 × 2030 | fixed preview height, 64-dot width rounding |
| width-boundary-128 | 128 × 200 | 128 × 2030 | fixed preview height |
| width-boundary-383 | 383 × 200 | 384 × 2030 | fixed preview height, 64-dot width rounding |
| width-boundary-384 | 384 × 200 | 384 × 2030 | fixed preview height |
| width-boundary-384-fit | 384 × 200 | 384 × 2030 | fixed preview height |
| width-boundary-385 | 385 × 200 | 384 × 2030 | fixed preview height, width cap |
| width-boundary-63 | 63 × 200 | 64 × 2030 | fixed preview height, 64-dot width rounding |
| width-boundary-64 | 64 × 200 | 64 × 2030 | fixed preview height |
| width-boundary-65 | 65 × 200 | 128 × 2030 | fixed preview height, 64-dot width rounding |
| width-boundary-800 | 800 × 200 | 384 × 2030 | fixed preview height, width cap |
| width-late-grow | 384 × 200 | 128 × 2030 | fixed preview height, width latching |
| width-late-grow-fit | 384 × 200 | 128 × 2030 | fixed preview height, width latching |
| width-late-shrink | 120 × 200 | 384 × 2030 | fixed preview height, width latching |

Validation: rebuilt the adapter against upstream revision
`e72ec442c94159bfe792c480c018690e234948e4` and reran all 120 ZQ610 inputs
through `build.render.render` and `build.compare.comparison`. All 120 native
canvases match; all 26 cases listed above are pixel-exact. Overall 117/120
images are exact. The remaining `text-0-B`, `text-0-I`, and `text-0-R` ink
differences are unrelated to canvas size (IoU 99.26%, 98.54%, and 99.09%).
Only codyps-zpl saved observations, images, and adapter identity were refreshed;
all other candidates retain their prior observations. The paired-profile
results also contained no dimension mismatches.

Regression checks: `bazelisk test //:canvas_profile_test //:pipeline_test
//:site_test` and the five tests in `benchmarks/test_zq610.py` passed. The real
adapter test covers both profiles, including fixed height, width rounding,
width cap, and width latching. Saved imports reject the old ZD621-profile rows.

The full `//:reports_saved` build passed and its recomputed five comparison
suites contain no codyps-zpl canvas mismatches. Site generation validated 1,138
HTML pages and all local links/images. The regenerated `canvas-height-120`
page reports 384 × 2030, 100% IoU, exact, with the ZQ610 profile recorded.
The site was generated locally in `_site_canvas_profile_fix`; it was not deployed.
