# Printer accuracy benchmark

The [font-free layout suite](../../test-data/layout-accuracy/README.md) isolates
offsets, page transforms, clipping, reversal and field orientation from glyph
shapes, with its own ZD621 preview references and comparison command.

For every generated resource in the repository, including performance and invalid-input reports, run `benchmarks/_work/venv/bin/python benchmarks/regenerate.py`. See the [complete generation inventory](../README.md#regenerate--test-the-harness). The accuracy-only commands below remain available.

**[Compare printer previews, library renders and differences](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/accuracy/comparisons/README.md)** by library or case. Every case includes all eight renderers, including error diagnostics and blank output.

The [checked-in report](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/accuracy/README.md) compares eight rendering adapters with a real ZD621's HTTP preview. The measured adapter file hashes are recorded in `results.json`; rebuilding adapters uses the source and dependency pins described in the parent benchmark guide. The codyps-zpl adapter uses the library’s default ZD621 compatibility profile with the case dimensions and 203 DPI. It is separate from the [performance suite](../README.md); timing and code-size measurements remain the historical run recorded there.

## Reproduce offline

First follow the parent benchmark setup to install the pinned dependencies and build all adapters. Then, from the repository root:

```sh
benchmarks/_work/venv/bin/python benchmarks/support.py
benchmarks/_work/venv/bin/python -m unittest discover -s benchmarks -p 'test_*.py'
benchmarks/_work/venv/bin/python benchmarks/accuracy/regenerate.py
```

This single regeneration command reruns all 133 accuracy cases, 598 feature
fixtures and eight external examples across all eight prepared renderers, writes results, rendered PNGs, difference images, plots and comparison
Markdown, then refreshes the dependent compatibility pages. It verifies the gallery
and generated compatibility pages before succeeding. It uses the existing adapter
builds in `benchmarks/_work/config.json`; rerun `benchmarks/prepare.py` first after
changing library sources or pins. It does not recapture printer references or rerun
the separate performance or invalid-input suites. Feature conformance is included.

The runner checks SHA-256 hashes, capture completeness and repeated-control pixels before rendering. No printer or external rendering service is contacted. Each case runs in a fresh process with a 45-second timeout; errors remain visible and score zero for nonblank references. GitHub Actions repeats these suites and uploads Markdown, plots, rasters and raw JSON. Accuracy differences are measurements, not CI failures; broken reference integrity or harness failures fail the run. Renderer crashes or timeouts remain in the reports and make full regeneration exit nonzero after writing all reports. Missing adapter executables or native libraries fail before measurement output is overwritten.

Each library comparison page shows compact difference thumbnails beside its per-test IoU values, linked to the full-resolution differences. The same images appear on individual test pages.

To regenerate only the plots and tables from saved measurements:

```sh
benchmarks/_work/venv/bin/python benchmarks/accuracy/regenerate.py --reports-only
```

Report generation verifies the complete case-by-renderer matrix, input and reference hashes, image metrics, and every difference image before generating the comparison pages. To check the saved images and pages without rewriting them:

```sh
benchmarks/_work/venv/bin/python benchmarks/accuracy/gallery.py docs/benchmarks/accuracy --check
```

## Capture a new reference deliberately

```sh
benchmarks/_work/venv/bin/python benchmarks/accuracy/capture.py \
  --host http://YOUR-203DPI-PRINTER/ \
  --output benchmarks/accuracy/new-reference
benchmarks/_work/venv/bin/python benchmarks/accuracy/run.py \
  --reference benchmarks/accuracy/new-reference
```

Use a new directory within this repository; capture refuses to overwrite an existing one. Review the identified model/firmware, images and manifest before adopting a new baseline. This implementation accepts identified 203-dpi printers only. It submits the fixed raster-only probes using **Preview Label**, never Print. The printer's preview mechanism uses its RAM object `R:CMPACC.ZPL` by default (`--object-name` overrides it); reserve a distinct name during capture. Rendering defaults are inserted into the fixture format in the same preview request, and requests are spaced two seconds apart. Preview PNG URLs are read from each response. This reduces collisions but does not isolate the printer’s global rendering state from other clients. No persistent downloads or physical label jobs are requested. The capture protocol follows [the existing printer client](https://github.com/codyps/zpl/blob/280fc0cf4d0a49c916463d936e4307a2a226928e/zebra-http-api/src/lib.rs).

There are 73 fresh argument cases plus one repeated control and 60 recaptured barcode cases. The barcode captures were refreshed at ^PW832 with a separate reset before every case; this command refreshes only the argument set. A new device reference creates a mixed-device corpus unless the barcode set is recaptured separately. Existing barcode captures were used in development and are not a holdout.

Foreground intersection-over-union is measured at the original origin, with transparency composited on white and a fixed gray threshold of 128. Canvas differences are padded white and separately reported, never cropped, resized or aligned away. Blank printer references are excluded from aggregate accuracy. Whole-canvas disagreement, missing/extra pixels, precision, recall, dimensions and exact-match flags remain in JSON. A valid alternative barcode encoding can differ visually; this does not measure scanner acceptance. Preview fidelity does not measure physical print quality.

The argument list and values are in [cases.py](cases.py), with the Zebra command-reference index in [the documentation](../../docs/zpl-command-index.tsv). Expand the corpus before drawing conclusions about an untested command, value, encoding, font, firmware or workload. Host fonts may affect fallback rendering. Every library receives the same input bytes; adapters only supply canvas dimensions and call public rendering APIs. The Rust FFI wrapper and Go adapter share an engine but their wrapper defaults and API paths can differ.

## Feature accuracy gallery

The [598-fixture gallery](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/accuracy/comparisons/features/README.md)
shares the accuracy metric, image layout and regeneration command. Compatibility
feature pages link to each fixture's eight renders and printer differences.
Feature means stay separate from the argument/barcode chart to avoid changing its
sampling weights. Missing or incomplete printer captures leave the fixture unscored;
invalid inputs never reach the printer. Capture and resume instructions are in the
[parent benchmark guide](../README.md#feature-renders-and-printer-differences).


Use `capture.py --corpus test-data/render-conformance --group torture` to capture
the combined rendering pages, then `benchmarks/conformance.py --reference DIR`
to compare matching source cases. See [the corpus guide](../../test-data/render-conformance/README.md).
Do not use the small-suite `accuracy/run.py` to report this larger corpus: its
historical barcode supplement and aggregate grouping belong to the original suite.

## Labelary renderer

Labelary participates as an eighth renderer against the same ZD621 printer
references, with the same foreground IoU, dimensions, exact-match and error rules.
The runner replays checked-in, hash-verified responses; it does not contact Labelary.
[Service capture provenance](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/labelary/README.md) records UTC
request/response timestamps and any exposed renderer version. The initial capture
exposed no renderer version. HTTP nginx and API v1 versions are not used as one.

Explicitly capture current service responses into a new directory:

```sh
benchmarks/_work/venv/bin/python benchmarks/labelary.py --capture --output benchmarks/_work/new-labelary
```

This sends the public corpus inputs to https://api.labelary.com at less than three
requests per second, preserving original PNG responses and failed HTTP responses.
Review and replace `docs/benchmarks/labelary` with the new snapshot to adopt it, then
run `accuracy/regenerate.py`. Existing snapshots are never overwritten by capture.
The capture covers the accuracy, conformance and external-label corpora. Offline
conformance runs can select `--only labelary`; `--only all` includes it too.

```sh
benchmarks/_work/venv/bin/python benchmarks/labelary.py --check
```

The feature corpus also includes [67 imported ZD621 controls](../../references/upstream-zd621/README.md)
with original upstream capture manifests. Five invalid UPC-E inputs are kept
out of printer-accuracy scoring. The corrected positive BR8 case uses eleven
uncompressed UPC-A digits and a nonblank original printer response.
