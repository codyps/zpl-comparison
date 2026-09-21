# Font-free layout accuracy

Twenty probes isolate label geometry from glyph outlines. Sixteen use only
rectangular graphics: field origins, label home, signed label shifts/top offsets,
combined offsets, mirror/invert combinations, edge clipping, and label/field
reversal. Four exercise `^FW` with caption-free Code128 symbols; these depend on
barcode rendering, but never on a font. Asymmetric landmarks make incorrect
translations and reflections visible. Clipping probes retain an in-bounds marker
so an empty renderer cannot pass by producing a blank page.

Text wrapping, text justification, and text baselines remain in the existing
[render conformance corpus](../render-conformance/README.md): they depend on font
metrics. These graphic probes do not establish correctness of those text paths.

This corpus uses the existing conformance runner and printer capture schema. It
is separate from the historical aggregate, so adding it does not change that
aggregate's sampling weights. [Case inventory](COVERAGE.md) and
[manifest](manifest.json) record exact inputs and command-reference pages.

The CI job's `bazelisk build //:reports` runs all 20 cases across seven local
renderers, compares them with the saved printer previews, and publishes the
[layout gallery](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/accuracy/comparisons/layout/README.md)
and [summary](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/layout-accuracy/README.md).
CI checks that all 140 render/comparison pairs are present in the action graph
and each comparison reads its printer reference. Labelary is excluded until
service responses are captured for these inputs. No printer is contacted by CI.

To build just this suite's images, differences and gallery pages:

```sh
bazelisk build //:reports --output_groups=suite_layout-accuracy
```

Fork pull requests use `//:reports_saved`, which regenerates the layout report
and gallery from the saved 140 renders and measurements without private source.

```sh
python3 test-data/layout-accuracy/generate.py --check
benchmarks/_work/venv/bin/python benchmarks/conformance.py \
  --corpus test-data/layout-accuracy \
  --only codyps-zpl,forge,labelize,ffi,go,zplr,binarykits \
  --reference benchmarks/accuracy/layout-reference \
  --output benchmarks/_work/layout-accuracy
```

The report scores unchanged rasters against the saved ZD621 previews using the
existing foreground IoU and exact-match metrics. It never aligns or resizes
images to hide positioning differences. The home/direct-origin pair also checks
exact raster equivalence within each renderer; agreement alone is not evidence
of printer fidelity. Labelary is omitted because its saved responses do not yet
include this corpus.

To capture a fresh baseline into a new directory:

```sh
benchmarks/_work/venv/bin/python benchmarks/accuracy/capture.py \
  --host http://YOUR-203DPI-PRINTER/ \
  --corpus test-data/layout-accuracy --object-name CMPLAY \
  --output benchmarks/_work/new-layout-reference
```

Capture identifies the model and firmware, resets rendering state per preview,
and repeats the first control at the end. This uses Preview Label, not physical
printing. Device identity, source/image hashes, and repeatability evidence are
saved in [the capture manifest](../../benchmarks/accuracy/layout-reference/manifest.json).
