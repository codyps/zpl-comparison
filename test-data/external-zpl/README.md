# External ZPL examples

Nine complete labels adapted from pinned, MIT-licensed public examples. Each
manifest entry links its original file, revision, license and SHA-256. Original
upstream files remain unchanged beside the explicitly named native-width variants.

| Example | Preview canvas (dots) |
| --- | --- |
| Shipping | 832 × 1218 |
| Product | 640 × 406 |
| Warehouse | 832 × 609 |
| Compliance | 832 × 1218 |
| SurePost | 832 × 1524 |
| Asset Data Matrix/PDF417 | 832 × 500 |
| Retail UPC/EAN (original encoding diagnostic) | 832 × 500 |
| Retail UPC/EAN (explicit UTF-8) | 832 × 500 |
| Stored resources | 448 × 220 |

Widths are multiples of 64 within the ZD621 preview limit, avoiding its width
rounding and centering offset. Lengths are explicit. The original asset example
requested 900 dots; its 832-dot variant clips content beyond the right edge rather
than scaling or moving it.

SurePost's preview variant omits `^MNY`, `^MFN,N`, and `^MCY`: these device-setting
commands changed the printer's media length during the first capture attempt.
Its label content, coordinates and orientation remain intact. The stored-resource
variant uses isolated `R:CMPEX` object names and explicit dimensions in both
formats. All adaptations are recorded in `derived_from` in the manifest.

## Printer references

All nine examples have HTTP Preview Label captures, not physical print/scan
measurements. Each capture applies the common rendering-state reset. The stored
example first uploads only its RAM graphic and `^DF` format through port 9100;
its final `^XF` label is submitted only to HTTP Preview. The manifest hashes both
the RAM setup and the exact preview submission. A repeated first-label control
must match before captures are accepted. No label-print command is submitted.

Labelary and all local adapters receive the same complete derived ZPL and requested
canvas. Renderer failures remain failures; they do not receive replacement images.
These are example layouts, not carrier certification tests or independent holdouts
for the libraries that authored them.

## Regeneration

Use the adapter setup in [the benchmark guide](../../benchmarks/README.md), then:

```sh
benchmarks/_work/venv/bin/python benchmarks/conformance.py --corpus test-data/external-zpl --only all --output docs/benchmarks/external-zpl
benchmarks/_work/venv/bin/python benchmarks/accuracy/features.py --suite external
```

Captures are an explicit separate operation. Preserve old evidence until fresh
source hashes, dimensions, submission hashes and the repeated control are verified.

## Retail encoding

The original example contains UTF-8 C2 B7 for a middle dot but has no `^CI28`.
The captured printer reset selects CI27, so the original capture represents
`Â·`; a renderer starting in CI0 instead interprets the same bytes through CP850.
The original source and [printer image](../../benchmarks/accuracy/external-reference/zplr-retail-upc-ean.png) are preserved as a diagnostic, with no
score because the initial encodings differ. The new `zplr-retail-upc-ean-utf8`
case adds only `^CI28` after `^XA`, has its own printer capture and repeatability
control, and is scored normally. This does not silently reinterpret original
bytes as UTF-8 or reuse the legacy-encoded reference for corrected text.
