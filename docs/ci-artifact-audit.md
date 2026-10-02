# CI artifact audit — 2026-10-02

CI should own current local renderer observations, source-support extraction,
invalid-input probes, and the reports computed from them. The source branch
currently carries a second, manually refreshed set of renderer observations,
and several report families only replay that evidence even on trusted builds.

This audit examined tracked files at `aed30e94ed15`, with the CI-warning and
missing-fixture repairs in the working tree. Sizes are uncompressed working-tree
bytes for tracked paths, not Git pack sizes. The 15 new fixture PNGs are excluded
from the inventory. This document records the pre-migration audit. The implemented CI and replay contracts are documented in [benchmarks/README.md](../benchmarks/README.md).

| Saved renderer output directory | Tracked files | MiB |
| --- | ---: | ---: |
| `docs/benchmarks/conformance/` | 4,668 | 27.98 |
| `docs/benchmarks/accuracy/` | 1,053 | 5.17 |
| `docs/benchmarks/layout-accuracy/` | 161 | 1.43 |
| `docs/benchmarks/external-zpl/` | 70 | 2.17 |
| `references/zq610-candidates/saved/` | 837 | 8.19 |
| **Total** | **6,789** | **44.96** |

These five directories account for 49% of the 91.67 MiB tracked working tree.
They contain local renders, replayed service images, and observation/provenance
JSON. Historical observations have archival value, but should not need manual
updates in the source branch to make a new fixture buildable.

1. **High: replace the manually maintained saved-render matrix.**
   [The main pipeline](../build/pipeline.bzl) already renders seven local engines
   and replays captured Labelary responses for trusted builds. Fork CI instead
   selects `//:reports_saved`, which requires a committed row for every current
   case/library pair and a PNG for each successful observation. This is the
   direct cause of the missing encoding-remap fixture failure. The two fixtures
   existed, but their 16 saved observations did not.

   Have trusted CI export immutable, hash-verified observation bundles, including
   failures, adapter identities, source/dependency pins, timestamps, and images.
   Keep a small baseline reference for fork/offline replay. Bundles need durable
   storage and explicit retention: the current seven-day site-preview artifact
   is insufficient. Match baseline entries against fixture bytes, dimensions,
   profile, and renderer identity; changed cases cannot silently inherit an old
   measurement. Public adapters can run on forks, while private-renderer results
   require a trusted bundle or an explicit unavailable state.

   Remove the live pipeline's dependency on saved result documents first.
   [MODULE.bazel](../MODULE.bazel) loads all five snapshots into the analysis
   catalog, and both [pipeline.bzl](../build/pipeline.bzl) and
   [zq610.bzl](../build/zq610.bzl) still use saved metadata on the live path.
   Suite definitions and reference manifests should supply that metadata.
   The new saved-matrix regression test is a guard for the existing contract;
   it should be replaced by bundle coverage/provenance validation when this
   migration removes the requirement to commit every local observation.

2. **High: run invalid-input probes in CI.**
   [The saved invalid-input results](https://github.com/codyps/zpl-comparison/blob/aed30e94ed1531a424b32eac8da60bd313ca2f21/docs/benchmarks/invalid/results.json) were
   measured on macOS on September 20. Ten recorded input hashes already differ
   from `HEAD`, including source/dependency pins and every language adapter's
   entry point. These mismatches predate the current warning fixes.
   [The pipeline](../build/pipeline.bzl) invokes `invalid.py --report-only` and
   `--check`; [those modes](../benchmarks/invalid.py) validate the fixture
   manifest and report, but do not execute adapters or compare their current
   identities to the saved run.

   Add repeated valid/invalid probe actions using the built adapters, retaining
   rejection, crash, timeout, and instability outcomes. Key cached behavioral
   observations on the complete executable/runtime identity, probe code, mode,
   and fixture. Publish their classifications from those results. Preserve any
   deliberately dated historical campaign separately.

3. **High: recompute command-support evidence from the selected sources.**
   [command-support.json](https://github.com/codyps/zpl-comparison/blob/aed30e94ed1531a424b32eac8da60bd313ca2f21/docs/benchmarks/command-support.json) records codyps/zpl
   revision `b6085d8e…` and Labelize `75cc2b36…`; the current source pins are
   `f75ee34b…` and `b9598a53…`. CI only runs
   [support.py](../benchmarks/support.py) with `--reports-only`, so publishing
   fresh renderer results does not refresh the source inventory.

   Make extraction a build action over the exact resolved source/package trees.
   Parameterize the collector's current `_work` paths and Cargo metadata input.
   Its additional generator-only libraries need their own pinned inputs; they
   should retain explicit dated evidence until wired into extraction. Keep
   human-authored argument notes and the capability template as source. Source
   presence remains a different measure from successful rendering.

4. **Medium: give historical public-label and paired-printer campaigns a
   current CI evaluation.**
   [Public examples](../benchmarks/public_examples.py) are deliberately dated
   observations, and CI's `--check` explicitly does not execute a renderer.
   Their directory contains 17 local PNGs (6.78 MiB), 39 computed difference PNGs,
   generated HTML/Markdown, comparison JSON, and decoder results.
   [The paired ZQ610/ZD621 report](../benchmarks/zq610_pages.py) verifies saved
   hashes and regenerates pages/diffs, but reuses `analysis.json` and 232 saved
   local renders. The separate ZQ610 candidate matrix already has live actions;
   that does not remeasure the whole paired campaign.

   Retain the original campaign provenance and publish current local renders
   against the existing printer captures in separate CI results. Extract the
   paired campaign's renderer/comparison work from the printer-capture script
   so it runs offline against the built adapter with explicit device profiles.
   Generate comparison JSON, differences, README, and HTML in Bazel outputs.
   Human findings can continue linking to immutable historical observations.

5. **Medium: compute decoder and aggregate failure results automatically.**
   [audit_public_barcodes.py](../benchmarks/audit_public_barcodes.py) produces
   `docs/public-examples/barcodes.json`, but no CI step invokes the decoder.
   The existing public-example validation only checks the recorded decoder
   input image hashes. Add its pinned decoder dependency and an action keyed
   on decoder identity and PNG bytes. Retain decoded payload evidence and the
   distinction between decoding success and printer pixel agreement.

   [audit_failures.py](../benchmarks/audit_failures.py) can generate the tracked
   `docs/total-failures.json` and `.tsv`, but CI currently runs only its unit
   tests. Add the inventory action after the current report aggregates. Keep
   [the authored failure analysis](total-failure-audit.md) as historical notes;
   link current counts to the generated inventory rather than maintaining them
   manually. Counts alone should not gate success because intentionally invalid
   inputs and unsupported features are part of the corpus.

6. **Low: stop storing redundant fixture reports; generate fixture bytes at
   build time only after adapting analysis inputs.**
   `test-data/layout-accuracy/COVERAGE.md` is generated and tracked, while the
   equivalent conformance coverage file is already ignored. Publish coverage
   from the generator and remove the tracked copy once its consumers use the
   output. The three generated fixture corpora also store their ZPL and manifests.
   [validate.py](../build/validate.py) already regenerates these and checks byte
   equality, so their synchronization has an automated guard today.

   Moving fixture generation ahead of Bazel analysis would remove that duplicate
   representation, but is lower priority than missing behavior measurements.
   Preserve exact submitted ZPL and historical corpus manifests inside capture
   archives: their hashes bind external observations to their original inputs.
   Imported upstream examples, licenses, and documented adaptations remain
   reproducibility inputs even when an upstream URL is available.

7. **Low: refresh popularity on a schedule or explicitly archive it.**
   [popularity.json](https://github.com/codyps/zpl-comparison/blob/aed30e94ed1531a424b32eac8da60bd313ca2f21/benchmarks/popularity.json) stores stars/forks and upstream
   last-push timestamps; it has no observation timestamp. The capability template
   calls it a dated snapshot, and no collector is wired into CI. A scheduled
   GitHub API collection can produce a timestamped publication artifact, with
   PR builds using a recorded snapshot. Avoid making report builds depend on
   successful live API requests. This metadata does not belong in benchmark
   correctness decisions.

**Keep as reproducibility inputs:** source and toolchain locks; fixture
definitions; adapters; fonts and licenses; imported source examples; printer
manuals; maintained methodology and findings; exact printer/SaaS requests,
responses, failure records, settings, timestamps, and capture-script provenance.
CI can verify captured evidence and recompute metrics from it. A local render
cannot replace a printer or Labelary observation, and a new service request
cannot reproduce an old response reliably. There are also 878 saved-suite
Labelary PNG copies (3.52 MiB) derived from canonical captures; those copies can
be generated while the original responses remain preserved.

**Already automated correctly:** trusted CI renders the common four suites and
the ZQ610 candidate suite through separate cached actions, recomputes comparisons,
and generates/validates the site. Performance runs outside the action cache on
each trusted run, and old committed performance samples have already been
removed. Deterministic behavior checks may reuse correctly keyed actions;
performance timings must be measured again.

**Suggested sequence:** add live invalid-input and source-support actions;
automate pure reports and decoder checks; add current evaluations for dated
campaigns; provision durable baseline bundles and adapt fork/offline replay;
then remove committed renderer snapshots and redundant generated files. Verify
that adding a fixture requires no manual local-render backfill, a renderer/source
change refreshes every relevant evaluation, and report-only changes reuse
rendering actions. Update the reproduction documentation alongside the migration:
[benchmarks/README.md](../benchmarks/README.md) still describes publishing to a
`generated` branch, while the current workflow publishes GitHub Pages artifacts.
