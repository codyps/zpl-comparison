# GX430t 300-DPI comparison references

34 cases cover scalable and bitmap text, rotations, Unicode, wrapping, origins,
page transforms, reversal, shapes, raster graphics and eight barcode families.
The baseline is the Zebra GX430t's original HTTP **Preview Label** response,
firmware V56.17.17Z, serial 32J193600198, captured October 18, 2026.
These are firmware previews, not physical print scans.

The sources and PNGs were imported without changes from
`codyps/zpl/zpl/tests/fixtures/gx430t-300-v1/main`. The original acquisition
receipt is retained as `provenance.json`, including its source revision, dirty-tree
qualification, timestamps, image URLs and hashes. `manifest.json` indexes the
selected files. The original reset, state pages and byte-identical start/end
controls are retained. The campaign was acquired before this comparison was
added; it is development evidence rather than an independent holdout.

The GX430t uses 12 dots/mm, marketed as 300 DPI. Its preview ignores `^LL` and
returns 2558 rows for this captured configuration. All selected previews are
832 × 2558. Sources retain their submitted `^PW`, `^LL` and inline reset bytes.
Renderers receive that exact source and native canvas. Comparisons never align,
pad, crop or rescale images. Different output dimensions remain visible and
unscored. The comparison site offers display-only ink crops and original images.

Every local adapter selects 300 DPI or 12 dots/mm through its public rendering
API. The three codyps/zpl adapters select the GX430t profile. Other engines use
their own firmware behavior and fonts. Neodynamic retains its evaluation stamp
and the existing chromatic-stamp exclusion policy. Labelary uses separately
captured 12-dpmm responses for all 34 cases, with original PNGs, request URLs,
HTTP headers, UTC timestamps and hashes in [labelary/captures.json](labelary/captures.json).
Its saved 8-dpmm responses are never reused. The 203-DPI controlled-font campaign excludes this suite because
its font bundle and printer captures do not cover this device/density.

From the repository root:

```sh
# Verify retained printer evidence, including repeated controls.
PYTHONPATH=benchmarks:. python3 benchmarks/gx430t.py
# Build only the fresh 34 × 14 matrix and its report.
bazelisk build //:reports --output_groups=suite_gx430t
# Build the complete report tree for site generation.
bazelisk build //:reports
```

The focused report is under
`bazel-bin/reports_actions/gx430t-report/docs/benchmarks/gx430t-300dpi/`.
The site category is `categories/gx430t-300dpi.html`. `//:reports_saved` replays
compatible observations from published bundles and labels missing observations.
Full builds export this suite into subsequent bundles.

To reproduce the import into a new checkout with no existing reference directory:

```sh
PYTHONPATH=benchmarks:. python3 benchmarks/gx430t.py \
  --import-from /path/to/zpl/zpl/tests/fixtures/gx430t-300-v1/main
```

Import and verification run offline. No printer requests or physical labels are
needed to rebuild comparisons.

## Labelary service responses

All 34 responses were acquired on October 22, 2026 using the
[Labelary API](https://labelary.com/service.html) at `12dpmm` and label index 0.
The GX430t remains the baseline. Offline builds verify and replay these service
responses; they never contact Labelary.

The API's canvas conversion is distinct from nominal 300 DPI: the measured
12-dpmm endpoint uses 304 dots per inch for dimensions. Dividing the target dots
by 300 produced 843 × 2592; dividing by 304, rounded upward to six decimal places,
produced the required 832 × 2558. The adopted URLs and actual dimensions are
recorded in the capture manifest. Every original ZPL byte is preserved, including
its inline reset and `^LL`; no image is resized or cropped to obtain this canvas.
API v1 and HTTP server headers do not identify a renderer build version.

```sh
# Verify the complete service snapshot offline.
PYTHONPATH=benchmarks:. python3 benchmarks/gx430t_labelary.py
# Acquire a new snapshot deliberately into an unused directory.
PYTHONPATH=benchmarks:. python3 benchmarks/gx430t_labelary.py --capture \
  --output benchmarks/_work/new-gx430t-labelary
```
