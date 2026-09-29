# Total comparison failure audit

This audit covers all 7,032 observations across five rendering suites and eight
libraries. It distinguishes execution failures, blank output against a nonblank
printer reference, zero ink overlap, and mismatched native canvases. Unscored
observations without a usable printer reference are not automatically failures.
Intentionally invalid inputs remain identified as such; rejecting them is not a
renderer defect. The separate invalid-input and performance suites do not measure
printer-image agreement.

## Comparison fixes

- **BinaryKits:** 59 saved ZQ610 attempts crashed in HarfBuzz with a null font
  asset. The Linux runtime did not include the fonts its viewer requires.
  The adapter now bundles the upstream WebApi's TeX Gyre Heros Cn Bold and
  DejaVu Sans Mono, with licenses and artifact hashes, and selects them through
  the public `FontManager` API. A real-adapter test verifies both fonts render
  without host font discovery and produce the same pixels. These substitute
  fonts are not Zebra resident-font captures.
- **zplr:** the adapter discarded both requested dimensions. All 26 ZQ610
  canvas mismatches were therefore measured with the wrong API configuration.
  The adapter now passes `width` and `height` to both render and probe calls.
  It also uses the public tokenizer to preserve counted binary graphic bytes
  as byte-valued string characters, while decoding ordinary text as UTF-8.
  Previously `readFileSync(..., 'utf8')` could replace graphic bytes with U+FFFD.
  Equivalent binary and ASCII-hex graphics now pass a full-image equality test,
  including accompanying UTF-8 text.
- **Text adapter input:** non-UTF-8 bytes outside zplr's supported binary spans
  are rejected explicitly. BinaryKits' Unicode-text entry point likewise no
  longer receives replacement characters substituted for undecodable input.
  Raw-byte API adapters continue receiving the original bytes.
- **Stale codyps/zpl evidence:** replaying the current pinned renderer recovered
  16 old conformance errors: retail captions; Code 93 control characters;
  character remapping; encodings 31 and 33-36; and field-hex NUL handling.
  Its complete five-suite observations were refreshed, with source revision,
  adapter identity, timestamps, and host recorded. There were no native canvas
  mismatches or zero-overlap scored renders in that refresh.

All source ZPL, printer captures, and Labelary responses remain unchanged.
The refresh helper replaces only selected libraries' observations and images;
its preservation behavior has a regression test. Per-library refresh provenance
is retained when generating saved reports.

## Verified recoveries

- 59 BinaryKits ZQ610 font crashes now render (119 rendered, one blank diagnostic).
- All 26 zplr ZQ610 native-canvas mismatches are gone.
- zplr's `raster-equivalent-binary` and `raster-binary-command-bytes` now render
  instead of producing blank output.
- 16 codyps/zpl conformance execution failures were stale and now render.
- Forge, Labelize, go-zpl, zpl-rs FFI, and Labelary observation rows were
  checked against the preceding commit and remain exactly unchanged.

## Final inventory and validation

The rebuilt reports contain **404 flagged observations out of 7,032**, down
from 500 before these fixes. There are **zero canvas mismatches**. The flags
comprise 258 execution failures/rejections, 110 zero-ink-overlap renders, and
36 blank outputs against nonblank references. These counts include deliberately
invalid inputs and genuine unsupported features.

| Library | Flagged before | Flagged after |
|---|---:|---:|
| codyps/zpl | 37 | 21 |
| BinaryKits | 90 | 35 |
| zplr | 38 | 13 |
| Forge | 221 | 221 |
| Labelize | 41 | 41 |
| zpl-rs FFI | 25 | 25 |
| go-zpl | 24 | 24 |
| Labelary | 24 | 24 |

The BinaryKits refresh explicitly rejects two raw-binary inputs that its text
API cannot represent; these were previously silently decoded with replacement
characters. Correcting fonts and canvas sizes can also reveal displaced or
blank ink, so recovered execution/canvas errors do not all become passing
pixel comparisons.

Validation passed: real native adapter contracts, canvas-profile tests, pipeline
and site tests, the failure-inventory unit tests, workflow lint, and the complete
`//:reports_saved` build. The final inventory below is generated from rebuilt
reports, including all recomputed comparisons, rather than only the saved
observation metadata.

## Remaining failures and harness assessment

| Library | Assessment |
|---|---|
| codyps/zpl | The 17 remaining invalid-input rejections are expected. Four explicit renderer limitations remain: `encoding-29` and `encoding-30` (UTF-16), `zplr-retail-upc-ean` (legacy non-ASCII text / missing glyph), and `zplr-stored-resources` (`^DF`/`^XF` storage). These match the renderer's documented unsupported-semantics errors, rather than adapter misuse. No renderer patch was needed for an incorrectly implemented supported operation found by this audit. |
| Forge | Exact input is passed to `ZplEngine::new` with dot dimensions and 203 DPI, followed by `to_png`. All 120 ZQ610 inputs fail its parser: the reset preamble contains `^CI` remap pairs; the parser consumes only the encoding number and then fails on remaining operands. Minimal real-adapter controls confirm a plain box renders, while adding `^CI0,0,0` or a third `^FO` operand fails. Other failures come from its parser, barcode backend, or inability to accept non-UTF-8 bytes through its string API. Removing unsupported commands would change the comparison input and is not a harness fix. |
| Labelize | The adapter passes original bytes to `ZplParser`, then invokes `Renderer::draw_label_as_png` with native dimensions at 8 dots/mm. Errors originate in its B64 parser, MaxiCode mode/payload handling, retail barcode validation, and PDF417 encoder. No harness repair identified. |
| BinaryKits | Font provisioning was a harness fault and is fixed. Remaining retail/PDF417 exceptions and binary-graphic limitations originate in the library. The stored-format failure is also upstream: its download analyzer strips the device/extension from a format name, but its recall analyzer retains the full name, so `R:CMPEX.ZPL` is not found. The adapter correctly submits the complete job to one analyzer/storage instance. |
| go-zpl | The adapter passes the full byte-preserving Go string to `Parse`, and uses `render.New(DPI203).WithSize(...).RenderPNG`. Blank/zero-overlap cases involve serial fields, QR positioning, justification, rotation, and text-block behavior. No process/setup failure or incorrect API invocation identified. |
| zpl-rs FFI | The adapter uses `render_bytes_with_options`, including explicit size, rather than a NUL-terminated text API. It shares the Go renderer's observed feature/positioning limitations. No harness repair identified. |
| zplr | Requested-canvas and binary-string conversion faults are fixed. Remaining blank/zero-overlap or explicitly unsupported input results are retained as measured library behavior. Its only public profile is `zpl-ii-2025`, so there is no mobile-printer profile to select. |
| Labelary | Saved HTTP requests use exact source hashes, requested dimensions, and 8 dots/mm. The two HTTP 404 results are intentionally invalid inputs that generated no labels. Remaining blank and displaced images are actual captured service outputs, not local adapter failures. No API recapture or pixel adjustment was performed. |

The external printer capture also records an inline state reset. Reconstructing
its exact submitted retail payload and checking `submitted_sha256` changes the
initial diagnostic from legacy-byte rejection to unsupported glyph U+00C2;
it still fails. Selecting UTF-8 would change the submitted label semantics,
not fix the harness. This was checked without making a new printer request.

Zero ink overlap is not necessarily failure to execute: QR/barcode/text output
can be displaced completely from printer ink. Native dimensions and the original
origin remain unchanged; no alignment, cropping, padding, or score tolerances
were added to improve these results. Third-party renderer code was not changed.

## Reproduce

```sh
bazelisk test //:adapter_contract_test //:canvas_profile_test //:pipeline_test //:site_test
PYTHONPATH="$PWD" benchmarks/_work/venv/bin/python benchmarks/refresh_candidates.py \
  --libraries codyps-zpl,binarykits,zplr --save --jobs 3
bazelisk build //:reports_saved --jobs=2
python3 benchmarks/audit_failures.py --output docs/total-failures.json
```

`total-failures.tsv` lists every flagged case; `total-failures.json` includes
per-suite/library counts and captured diagnostics. The inventory intentionally
retains invalid-input rejections and genuine library limitations.
