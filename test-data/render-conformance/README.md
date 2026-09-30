# ZPL rendering conformance corpus

**600 standalone ZPL files**, exercising **68 content-command families**: 581 valid/boundary probes and 19 malformed or out-of-range inputs. Four dense “torture labels” combine many features on one page. The focused files explain failures the dense pages expose, much like browser rendering conformance tests.

[Complete command coverage and case catalog](https://github.com/codyps/zpl-comparison/blob/generated/test-data/render-conformance/COVERAGE.md) · [Manifest](manifest.json) · [Generator](generate.py) · [Existing printer accuracy report](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/accuracy/README.md)

These are tests of ZPL, not examples restricted to what this repository currently supports. No downloaded fonts, stored graphics/formats, disk operations, RFID, network configuration, print quantity, media calibration, darkness, speed or cutter commands are used. `^GF` graphics are inline. Canvas dimensions, orientation, mirroring, encoding and advanced text layout are included because they determine label pixels; they are not printer setup tests.

## Start with the combined pages

| File | Features combined |
| --- | --- |
| [Typography atlas](cases/torture/torture-typography.zpl) | Resident fonts, asymmetric glyphs, sizes, upside-down text and panel boundaries |
| [Geometry grid](cases/torture/torture-geometry.zpl) | 36 panels of circles, diagonals, rounded boxes, thickness, odd/even dimensions and rotated text |
| [Shipping label](cases/torture/torture-shipping-label.zpl) | Wrapping, justification, hanging indent, QR, Code128, Data Matrix, PDF417, reverse text and rotations |
| [Overlap stress](cases/torture/torture-overlap.zpl) | 96 overlapping black/white rounded shapes; draw order is observable |

No page prints “PASS” as an oracle. A renderer producing an image has not necessarily passed. Compare against printer captures or the documented equal-raster relationships.

The `symbol-aztec`, `symbol-aztec_alias`, and `symbol-aztec_rune` cases assess
barcodes without the character-remapping reset prefix in the ZQ610 submissions.
Keep those exact printer submissions as separate integration observations.
`encoding-remap-identity` tests `^CI0,0,0` independently against the identical
ASCII label using plain `^CI0` in `encoding-remap-control`. Both must render
nonblank, equal rasters; two failures cannot pass the relationship. This checks
identity-remap syntax and unchanged text, while `encoding-remap` exercises a
non-identity mapping. The pair uses a local equal-raster oracle and is excluded
from printer capture; it has no printer fidelity score.

## Focused coverage

For layout measurements independent of glyph shapes, see the separate
[20-case font-free layout accuracy corpus](../layout-accuracy/README.md).

| Area | Examples and edge cases |
| --- | --- |
| Fonts | All A–Z/0–9 selectors, bitmap/scalable metrics, all four rotations, zero/default dimensions, 1-dot text, odd/even scale boundaries, anisotropic scaling, ascenders/descenders, punctuation |
| Text data | Empty text, leading/trailing/repeated spaces, a 3072-byte field, literal FV, FH escapes including prefixes/NUL/DEL, FE concatenation and forward/backward substrings, inline FN reuse |
| Text layout | FO versus FT, three justification modes, baseline crosshairs, FP horizontal/vertical/reverse and tracking, FB L/C/R/J, narrow blocks, long words, overflow, signed line spacing, indent and explicit line breaks; TB rotations, wrap and height truncation |
| Encoding | UTF-8, UTF-16 BE/LE, legacy character sets, remapping, combining marks, RTL/mixed scripts, CJK, supplementary and missing glyphs, nonbreaking/zero-width spaces, PA bidi/shaping/OpenType/default-glyph flags |
| Coordinates | Home/shift/top offsets, negative shifts, all four field rotations, mirror/invert combinations, pixel boundaries, partial/full clipping, off-page origins |
| Painting | Box thickness/rounding 0–8, tiny/degenerate shapes, circles/ellipses/diagonals, white erasure, reverse/XOR overlap, double reversal, GS selectors A–E in every orientation |
| Inline graphics | Hex, counted binary, B64, Z64, CRC, row-fill and row-repeat RLE, multiple strides, odd origins, clipping, binary payloads resembling commands |
| Barcodes | All 29 command spellings in the archived symbol corpus, aliases and variants; widths/ratios, captions/above-text/rotations, checksums, Code128 modes/subsets/FNC1, QR model/EC/mask/module size, Data Matrix legacy/ECC200/rectangular dimensions, PDF417 EC/truncation/structured append and FM exclusions |
| State and scale | Font/barcode defaults versus overrides, field-local FH/FR/FE, inline numbered fields, initial SN/SF values, 1/48/400 fields, combined labels |
| Negative inputs | Bad enums, numeric ranges, encodings, hex escapes, raster count/stride, base64/CRC and symbol payloads; separate behavior observations, not valid-label fidelity scores |

The manifest records exact file bytes (SHA-256), purpose, validity, font dependence, dimensions, commands and Zebra guide pages. The 24 compact probes are 640×320 dots, covering font baselines, wrapping, geometry, barcode state and compositing; see [their source inspiration](INSPIRATION.md). Most other labels are 832×1218 dots; imported isolated probes retain their original 832×300 canvas and barcode samples use 832×1218. Widths are multiples of 64 dots: the ZD621 HTTP preview rounds 812 to 832 and centers content ten dots to the right. Ordinary symbol comparisons exclude that transport behavior. `generate.py --native-preview --output DIR` adds explicit paired rounding controls in a separate diagnostic corpus. Dimensions are per-case, not inferred from filenames. Binary fixtures really contain bytes: do not rewrite them through a text editor or normalize line endings.

## Reproduce and run

Regeneration and integrity checking need only Python 3.12+:

```sh
python3 test-data/render-conformance/generate.py
python3 test-data/render-conformance/generate.py --check
```

After [building the pinned benchmark adapters](../../benchmarks/README.md), run locally without contacting a printer:

```sh
benchmarks/_work/venv/bin/python benchmarks/conformance.py --only codyps-zpl --include-invalid
benchmarks/_work/venv/bin/python benchmarks/conformance.py --only all --group torture
benchmarks/_work/venv/bin/python benchmarks/conformance.py --only codyps-zpl,zplr --group graphics
```

Use repeated `--group` options to select families, `--timeout` to set a per-case process timeout, and `--output` to retain another report. Default output is the ignored `benchmarks/_work/conformance/` directory: Markdown, JSON and PNGs. Every case gets a fresh process. Errors remain visible; crashes/timeouts fail the run after saving the report. Unsupported features and visual differences are observations, not an assertion that all current libraries must implement the entire corpus. Negative cases are opt-in and kept in a separate table.

GitHub Actions verifies regeneration and runs all eight renderers against the corpus, including negative cases. The run's conformance report is uploaded with the benchmark artifact. It does not use a live printer or pretend generated images are printer references.

## Actual printer references

The checked-in capture provides **511 hash-matched printer previews** with a stable repeated control. Six eligible previews are unavailable; 14 invalid inputs are excluded from printer submission. [Browse every render and available difference](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/accuracy/comparisons/features/README.md). To create a separate capture, start with the four combined pages:

```sh
benchmarks/_work/venv/bin/python benchmarks/accuracy/capture.py \
  --host http://YOUR-203DPI-PRINTER/ \
  --corpus test-data/render-conformance --group torture \
  --output benchmarks/_work/new-printer-reference
benchmarks/_work/venv/bin/python benchmarks/conformance.py \
  --only all --group torture \
  --reference benchmarks/_work/new-printer-reference
```

Omit `--group` to capture every eligible case. Capture skips negative inputs, verifies fixture hashes and command scope, resets rendering defaults within each submitted format, and repeats the first case at the end. It uses the dedicated temporary `R:CMPACC.ZPL` preview object, never a physical print request. Reserve that object name and inspect the recorded model/firmware and images. See [capture details](../../benchmarks/accuracy/README.md).

Comparison uses unchanged source bytes and the existing foreground IoU metric with no registration or resizing. Missing reference cases remain N/A. Blank references are unscored; renderer errors count as zero only when a corresponding nonblank reference exists. References with mismatched hashes or unstable repeated controls are rejected.

## Equal-raster relationships

Five groups support checks without assuming any library is the oracle:

- Hex, binary, B64 and Z64 encodings of one asymmetric 16×8 bitmap.
- Hex versus row-fill RLE of alternating white/black rows.
- Hex versus repeat-count/row-repeat RLE of repeated `AA55` rows.
- Plain ASCII, FH-escaped ASCII and the same field with an FX comment.
- Direct field placement versus the equivalent LH+FO translation.

At least two successful **nonblank** outputs are needed for a meaningful equality check. Equality is exact after the benchmark's fixed threshold; two blanks or two failures are inconclusive. These relations can detect internal inconsistency, but cannot establish printer fidelity.

## Scope limits and further expansion

“Coverage” means a feature has a concrete test, not exhaustive conformance. Parameter cross-products, firmware differences, symbol capacities and every malformed byte stream are unbounded. The command table explicitly classifies all 224 spellings in the bundled reference, including those excluded from rendering scope.

Font-ID availability, Unicode repertoires, shaping and fallback vary by model/firmware and installed resident fonts. A font-dependent case makes no promise that those glyphs are installed. Named font files and font-link/download operations are excluded. Clock-derived fields (`^FC`) are excluded because they require a controlled clock. First-label SN/SF rendering is included, but multi-print increment/rollover is excluded with print-job control. Prefix/delimiter/language/unit configuration is excluded; literal prefixes inside FH and counted binary content are tested.

`^GFC` proprietary compressed-binary encoding does not yet have an independently verified encoding vector here; A/B plus ASCII RLE/B64/Z64 are covered. QR manual/structured-append payload grammar and every composite-barcode option need more vectors. The 60 inherited barcode cases were used in development and are not independent holdout data. Large off-canvas coordinates are bounded clipping probes, not allocation or denial-of-service stress tests.

Authority: [Zebra Programming Guide P1134473-11EN Rev A](../../docs/zpl-zbi2-pg-en.pdf), notably text pp. 186–217, typography pp. 60–62/154–159/315/356, barcodes pp. 64–150 and layout pp. 293–297/319/322/329. Per-case command sections are recorded in the manifest. The suite generator, not codyps/zpl renderer acceptance, determines the fixture set.

The [imported ZD621 controls](../../references/upstream-zd621/README.md) add 67
exact upstream inputs, including five explicitly invalid UPC-E cases. Their
original printer responses and capture provenance are retained independently
of the older capture batch. The positive `symbol-databar_upce` uses its corrected
832-dot capture; other historical barcode-family cases retain their 812-dot inputs.
