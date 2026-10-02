# Findings from public ZPL documents

On 2026-10-02, **5 of 22 labels matched the ZD621 preview pixel-for-pixel,
12 rendered with differences, and 5 returned local rendering errors**.
All 22 printer previews were nonblank, at the expected native dimensions.
The 23rd preview repeated the first and matched exactly.

Renderer: zpl `6aa0435f057f048f0b238e2f86ea06e8de4d12e0`, clean checkout,
explicit `ZD621_203_DPI` profile. Printer: ZTC ZD621-203dpi ZPL, firmware
V93.21.33Z. These are HTTP Preview Label responses, not physical print/scan results.

[Complete table](README.md) · [Interactive gallery](index.html) ·
[zpl counts, hashes and errors](results.json) · [Labelary comparisons](labelary-results.json) ·
[Pinned source provenance](../../test-data/public-zpl/sources.json)

## Exact labels

Labelixa Data Matrix serial, shelf label, and each of the three separately
extracted batch labels match across their complete native canvases. This is five
observations, including three closely related batch pages, not five independent
design families. No barcode decoder claim is needed to establish these pixel matches.

## Barcode geometry differs even when payloads agree

The Labelixa QR URL label has **37.249% foreground IoU**, with 17,974 printer-only
and 12,145 renderer-only pixels. The QR origins agree at `(90,69)` and modules are
8 dots wide. The printer uses a 264×264-dot symbol (33×33 modules); zpl uses
232×232 dots (29×29 modules). Both independently decode to
`https://example.com/product/48213`. This is a symbol size/encoding difference,
not merely an automatic-mask or alignment mismatch. Text also has differences.

The Labelixa carrier-style shipping label has **76.908% foreground IoU**.
Its PDF417 has a 308×132-dot occupied rectangle on the printer versus
274×162 dots locally, both starting at `(40,600)`. Both independently decode to
the same source bytes, including the literal `_1E`/`_1D` sequences. The source
does not enable `^FH`, so these are not decoded separator bytes. Its Code 128
tracking barcode decodes identically too. Whole-label errors also include text.

These payload observations use zxing-cpp 3.1.1 and are separately recorded,
with input PNG hashes, in [barcodes.json](barcodes.json). Successful decoding
does not establish printer geometry, standards conformance or carrier acceptance.

## Other rendering differences

The other ten successfully rendered, differing layouts range from **77.652% to
96.173%** whole-label foreground IoU. The inspected difference images show font
shape/advance differences, including mixed `^CF0` sizes and rotated text.
For example, the Shopify label has 1,638 underpaint and 1,709 overpaint pixels;
its visible difference is in the text, while the barcode bars overlay exactly.
The GS1 shipping label similarly shows differences in text around matching bars.
These observations do not replace per-field text IoU or systematic non-text region
checks; the saved primary metric is full-canvas foreground IoU.

## Local errors versus printer behavior

| Upstream document | Exact local diagnostic | Interpretation of the evidence |
| --- | --- | --- |
| BinaryKits Example2-102x170 | `drawing must end with FS before another command` at byte 4589 | The source moves from inline `^GF` data to another `^FT` without `^FS`; the printer produces a label. This is a tolerance difference. |
| BinaryKits Example4-102x152 | `QR field requires an error-correction switch` at byte 122 | The QR data begins `Package…` without its control prefix. The printer produces a QR that independently decodes as **`kage 4 in the Storage Box 2B`**: acceptance loses the initial `Pac`. It is not evidence that the intended payload printed correctly. |
| BinaryKits Example5-75x202 | `unsupported Code 39 character` at byte 1177 | The source contains unsubstituted `%s`. The captured symbol independently decodes as `~` under Code 39 Extended. This is a literal-template diagnostic, not a completed shipment label. |
| BinaryKits Example6-75x254 | `invalid barcode dimensions` at byte 1606 | The source requests `^BY12,2.2`; the printer draws very wide rotated bars, clipped at the bottom of the native canvas. The independent decoder found no symbol; this is not a successful barcode correctness control. |
| BinaryKits Example8-64x152 | `unsupported Code 39 character` at byte 1369 | The source contains unsubstituted `{0}` barcode data; the printer's two symbols independently decode as `0`. No substitution or repair was made. |

Offsets refer to the documented preview variants, not the untouched upstream
files. Full error diagnostics, including process exit status, remain in results.
The comparison site shows these failures and leaves their scores unset rather
than assigning fabricated images.

## Labelary comparison

All 22 Labelary requests returned nonblank native-size PNGs on 2026-10-02.
**None matched the printer pixel-for-pixel**; foreground IoU ranges from
**34.410% to 95.126%**. Among the 17 labels both renderers produced, zpl has
higher foreground IoU on 14 and Labelary on three: carrier-style shipping,
Shopify product, and BinaryKits Example3-54x86. This corpus is not a representative
ranking of general renderer quality. The five local errors remain unscored.

Labelary's carrier-style label reaches **86.058%** IoU versus zpl's **76.908%**.
Its independently decoded PDF417 occupies the same 308×132-dot bounding rectangle
as the printer and encodes the same literal payload. Equal bounds and decoded
bytes alone do not establish pixel-exact symbol geometry.

Labelary's QR URL label reaches **34.410%** IoU versus zpl's **37.249%**. Its QR
decodes to the same URL and has a 232×232-dot bounding rectangle at `(90,70)`;
the printer uses 264×264 dots at `(90,69)`. Neither service acceptance nor
successful decoding resolves this difference in geometry.

The five cases rejected by zpl render in Labelary with **60.691%–89.884%** IoU.
The independent decoder also finds the truncated `kage…` QR payload, `%s` decoded
as `~`, and `{0}` decoded as `0`; it finds no barcode in Example6. These are
diagnostic observations, not evidence that the intended shipment data is correct.
The extended [barcode audit](barcodes.json) preserves all previous observations.

The exact service PNGs and per-request metadata are retained in
[captures.json](../benchmarks/labelary/captures.json). All 762 previous service
observations are unchanged. No Labelary renderer version was exposed, so these
results are identified by their UTC capture times. The printer remains the
reference; no live service calls occur when generating comparisons. Other
libraries have no observations in this dated campaign.

## Follow-up priorities

1. Isolate the QR version/segmentation choice and PDF417 automatic dimensions with
   fresh, valid payload controls before changing compatibility behavior.
2. Measure the new text sizes/advances with independent holdouts; do not alter
   captured font strikes or loosen existing accuracy baselines for these labels.
3. Separate strict syntax/parameter validation from measured firmware tolerance
   for missing field separators and invalid barcode inputs. A tolerated but
   truncated payload should not be advertised as correct rendering.

This campaign changes comparison fixtures and tooling only. It does not fix
the renderer or change any existing core regression expectation.
