# Printer accuracy benchmark

**[Compare printer previews, library renders and differences](../../docs/benchmarks/accuracy/comparisons/README.md)** by library or case. Every case includes all seven renderers, including error diagnostics and blank output.

The [checked-in report](../../docs/benchmarks/accuracy/README.md) compares seven rendering adapters with a real ZD621's HTTP preview. The current codyps-zpl row uses the working source tree in the sibling zpl checkout (source hash and base commit in results.json), including uncommitted accuracy fixes. The pinned adapter rebuild reproduces the older library until its pin is advanced. It is separate from the [performance suite](../README.md); timing and code-size measurements remain the historical run recorded there.

## Reproduce offline

First follow the parent benchmark setup to install the pinned dependencies and build all adapters. Then, from the repository root:

```sh
benchmarks/_work/venv/bin/python benchmarks/support.py
benchmarks/_work/venv/bin/python -m unittest discover -s benchmarks -p 'test_*.py'
benchmarks/_work/venv/bin/python benchmarks/accuracy/run.py
```

The runner checks SHA-256 hashes, capture completeness and repeated-control pixels before rendering. No printer or external rendering service is contacted. Each case runs in a fresh process with a 45-second timeout; errors remain visible and score zero for nonblank references. GitHub Actions repeats both suites and uploads Markdown, plots, rasters and raw JSON. Accuracy differences are measurements, not CI failures; broken reference integrity or harness failures fail the run.

To regenerate only the plots and tables from saved measurements:

```sh
benchmarks/_work/venv/bin/python benchmarks/accuracy/report.py docs/benchmarks/accuracy
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

Use a new directory within this repository; capture refuses to overwrite an existing one. Review the identified model/firmware, images and manifest before adopting a new baseline. This implementation accepts identified 203-dpi printers only. It submits the fixed raster-only probes using **Preview Label**, never Print. The printer's preview mechanism uses its RAM object `R:TEST1.ZPL`; reserve that name during capture. No persistent downloads or physical label jobs are requested. The capture protocol follows [the existing printer client](https://github.com/codyps/zpl/blob/280fc0cf4d0a49c916463d936e4307a2a226928e/zebra-http-api/src/lib.rs).

There are 73 fresh argument cases plus one repeated control and 60 recaptured barcode cases. The barcode captures were refreshed at ^PW832 with a separate reset before every case; this command refreshes only the argument set. A new device reference creates a mixed-device corpus unless the barcode set is recaptured separately. Existing barcode captures were used in development and are not a holdout.

Foreground intersection-over-union is measured at the original origin, with transparency composited on white and a fixed gray threshold of 128. Canvas differences are padded white and separately reported, never cropped, resized or aligned away. Blank printer references are excluded from aggregate accuracy. Whole-canvas disagreement, missing/extra pixels, precision, recall, dimensions and exact-match flags remain in JSON. A valid alternative barcode encoding can differ visually; this does not measure scanner acceptance. Preview fidelity does not measure physical print quality.

The argument list and values are in [cases.py](cases.py), with the Zebra command-reference index in [the documentation](../../docs/zpl-command-index.tsv). Expand the corpus before drawing conclusions about an untested command, value, encoding, font, firmware or workload. Host fonts may affect fallback rendering. Every library receives the same input bytes; adapters only supply canvas dimensions and call public rendering APIs. The Rust FFI wrapper and Go adapter share an engine but their wrapper defaults and API paths can differ.

## Larger rendering conformance corpus

Use `capture.py --corpus test-data/render-conformance --group torture` to capture
the combined rendering pages, then `benchmarks/conformance.py --reference DIR`
to compare matching source cases. See [the corpus guide](../../test-data/render-conformance/README.md).
Do not use the small-suite `accuracy/run.py` to report this larger corpus: its
historical barcode supplement and aggregate grouping belong to the original suite.
