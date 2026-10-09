# Repeatable ZPL library comparison

**[Read the comparison site, plots and tables](https://codyps.github.io/zpl-comparison/categories/performance.html).**
The root README links to these detailed reports. [Library capabilities and selection](https://codyps.github.io/zpl-comparison/examination.html) distinguish parsers, renderers and generators.

[Command/argument inventory](https://codyps.github.io/zpl-comparison/examination.html) and [printer accuracy reproduction](accuracy/README.md) extend the comparison with offline captured references.

[Invalid-ZPL rejection tests](invalid/README.md) run paired valid/invalid inputs across parser and renderer APIs, with repeated executions and explicit error/crash classification.

The [rendering conformance corpus](../test-data/render-conformance/README.md) adds focused and combined test files defined by its generated manifest. Its [shared accuracy gallery](https://codyps.github.io/zpl-comparison/categories/conformance.html) shows each printer preview alongside all configured renderer outputs and pixel differences. Invalid inputs run offline only. Feature scores are reported separately from the argument/barcode chart because the sampling differs.

The [external label corpus](../test-data/external-zpl/README.md) contains pinned upstream examples with documented native-canvas adaptations,
plus an explicit UTF-8 retail variant with its own printer reference. [Execution report](https://codyps.github.io/zpl-comparison/categories/external-zpl.html).
Regenerate its images, JSON and Markdown with:

```sh
benchmarks/_work/venv/bin/python benchmarks/conformance.py --corpus test-data/external-zpl --only all --output docs/benchmarks/external-zpl
```

The [October 2026 public-document campaign](../test-data/public-zpl/README.md) adds
22 labels from Labelixa and BinaryKits, ZD621 previews, and all eleven renderers.
[Historical findings](../docs/public-examples/FINDINGS.md) and [current CI gallery](https://codyps.github.io/zpl-comparison/categories/public-zpl.html).
CI reruns every local renderer, replays the saved Labelary responses, and regenerates
the native comparisons and decoder evidence offline.

## Font-controlled rendering

[Font-controlled comparisons](fonts/README.md) supply recovered resident bitmap
fonts and shared TrueType substitutes through supported public APIs. Libraries
without font replacement retain their fixed fonts and are labeled accordingly.
The controlled baseline uses fresh ZD621 and ZQ610 Plus previews with the same
font bundle uploaded to printer RAM.
Build `//:reports_fonts` for the separate report tree; the original `//:reports`
continues to use the existing defaults.

## Node / WASM codyps/zpl

`codyps-zpl-node` builds `@codyps/zpl` from the `main` commit recorded in
`sources.lock.json`, using the same source revision as the native Rust adapter.
Publication CI advances both to `main`; local builds use the recorded revision.
No npm release is substituted for Git source.
`bazel build //:library_codyps-zpl-node` vendors the upstream locked Cargo
dependencies, compiles Wasm offline, and deploys the Node package with its runtime.
The Rust Wasm target and wasm-bindgen 0.2.128 are pinned in the toolchain lock.
For `prepare.py --only codyps-zpl-node`, install that target and CLI locally first.
The adapter participates in rendering, invalid-render input, accuracy and performance
comparisons. Its public API has no standalone parser or custom font provider.
The shared font-download bundle exceeds its 1 MiB input limit, so font-controlled
comparisons label this adapter as using fixed resident fonts.

## Run

Supported hosts: Linux and macOS. Install Rust/Cargo, Go ≥1.25, Node ≥24 with npm, .NET SDK 8, Python ≥3.12, Git and a native C toolchain. Build tools download dependencies; measured operations never contact a rendering service or printer. Use an idle machine and avoid concurrent builds while measuring.

```sh
python3 -m venv benchmarks/_work/venv
benchmarks/_work/venv/bin/pip install -r benchmarks/requirements.txt
benchmarks/_work/venv/bin/python benchmarks/prepare.py
benchmarks/_work/venv/bin/python benchmarks/run.py
```

Results replace `docs/benchmarks/results.json`, `README.md`, plots and captured samples. To preserve another host's measurements:

```sh
benchmarks/_work/venv/bin/python benchmarks/run.py --output benchmarks/_work/my-host
```

Rebuild only selected adapters with `prepare.py --only codyps-zpl,toolchain`; this creates a config containing those adapters. Select a subset of an existing config with `run.py --only codyps-zpl,toolchain`. All build/download/cache files are ignored. `BENCH_CARGO` and `BENCH_DOTNET` select specific executables. Standard `CARGO_HOME`, `CARGO_TARGET_DIR`, `GOPATH`, `GOCACHE`, `GOMODCACHE`, `NUGET_PACKAGES` and `DOTNET_CLI_HOME` overrides are respected; otherwise caches are kept under `_work`.

CI measures parsing and PNG rendering for the eleven Bazel-built renderer adapters (rendering only where no standalone parser is exposed) on every trusted run, after compilation and report generation finish. `bazel run //:performance` executes outside the action cache: cached binaries are reused, but timings are always recollected. Five fresh processes per cell record batch timings; five separate fresh processes record peak RSS with a fixed operation count. Results retain output checks, host information, adapter hashes and CI run identity. The `renderer-performance` artifact and published site use these new results. Fork previews omit performance because they cannot build the private source.

Old checked-in performance results and samples have been removed. The broader manual harness above remains available for generator-only libraries and source/deployment size surveys; those measurements are not presented as current CI results. Fixed input fixtures and a stable shuffle make runs comparable; measured durations are never fixed or replayed.

To run the same CI performance collection locally after building `//:render_libraries`:

```sh
bazel run //:performance -- --libraries "$PWD/bazel-bin" --fixtures "$PWD/benchmarks/fixtures" --output "$PWD/benchmarks/_work/performance"
```

Use a new output directory per run. Individual unsupported workloads retain diagnostics; a missing deployment or an adapter with no successful measurements fails the run.

If `/tmp` is a small memory-backed filesystem, point native build and report scratch space
at an existing disk directory with `--action_env=ZPL_BUILD_TMPDIR=/absolute/path`.

## Pins

The 2026-10-02 renderer search adds `zebrash` (Go 1.38.0),
`zpl-renderer-js` (4.0.0, wrapping the same Zebrash release in WASM), and
`zebrash-ts` (`@zebrash/node` 1.0.4). All three join the ZD621 argument,
conformance, external-label and layout suites, the ZQ610 candidate matrix,
invalid-input probes and CI performance collection. The public-document and
paired-printer campaigns also run the complete renderer matrix: 22 public inputs
and 116 paired cases at each printer's native canvas, across all eleven renderers.
Missing cells fail matrix validation; renderer errors remain explicit observations.
Public barcode decoding and the failure inventory include every renderer.

`bazel build //:reports` regenerates these campaigns with the same pinned adapters
as the other suites. Saved Labelary responses are matched by exact source hash
and requested dimensions. The paired ZQ610 responses reuse the candidate captures;
the paired ZD621 responses are recorded in `references/paired-labelary`.
`python benchmarks/paired_labelary.py` verifies them offline; `--capture` explicitly
submits missing public fixtures to Labelary. No printer recapture is needed.
Additional PHP, Android, SVG and service projects are documented in the
[maintained survey](templates/capabilities.md), with unmeasured status explicit.

Zebrash uses a separate `adapters/zebrash/go.mod` / `go.sum`; each new Node
adapter has its own `package-lock.json` and isolated deployment dependency tree.
WASM bytes and Node fonts load from local packages. The adapters pass the native
canvas at 8 dots/mm, enable inverted labels, and retain monochrome PNG defaults.
WASM initialization is outside warm timing and inside process RSS; Base64-to-PNG
decoding is timed. The wrapper has no parse-only lane. Source-size accounting
for it includes wrapper sources, not the embedded Go dependency, whereas its
deployment size includes the packaged engine. Native Zebrash and its TypeScript
port create fresh parser/drawer state per operation.

- [`sources.lock.json`](sources.lock.json): immutable source commits for the Go engine, Python package and source-size survey. Git checkouts must be clean when changing revisions.
- [`adapters/rust/Cargo.lock`](adapters/rust/Cargo.lock): exact Rust dependency graph. Each binary is built separately with one feature; `--all-features` is **not** a supported build. codyps/zpl and its raster dependency are path dependencies.
- [`adapters/node/package-lock.json`](adapters/node/package-lock.json): exact Node package graph and integrity hashes; `npm ci`. The pinned `skia-canvas` installer supplies its native component.
- [`adapters/go/go.mod`](adapters/go/go.mod) / [`go.sum`](adapters/go/go.sum): direct Go adapter; engine source also pins its own module graph. `-mod=readonly` is used for builds. The Rust wrapper's `LIBZPL_PATH` points at this source-built Go shared library.
- [`adapters/dotnet/packages.lock.json`](adapters/dotnet/packages.lock.json): exact NuGet graph and content hashes; locked restore. .NET is framework-dependent.
- [`requirements.txt`](requirements.txt): Python plotting/PNG decoder versions; these are outside timed operations except Pillow's import in the Python builder. The complete transitive graph and distribution hashes are pinned in [`../build/requirements.lock.txt`](../build/requirements.lock.txt).

Update pins explicitly, regenerate dependency locks using the relevant package manager, inspect API changes, then rebuild and rerun. Never compare two reports without checking their host, versions, fixtures and lock hashes. The JSON includes hashes of actual measured codyps/zpl source files so an uncommitted source change remains identifiable.

## Workloads and API boundaries

All renderer inputs are the same checked-in, single-label, ASCII ZPL bytes, at **400×300 dots**, nominal 203 DPI / 8 dots per mm. No implicit default-size comparison. Fixtures exercise boxes, one font-0 text field, Code 128, QR, and 48 small text fields. The explicit dimensions make nominal 203-versus-203.2 DPI immaterial to the canvas size. Fixtures reference the bundled [Zebra Programming Guide](../docs/zpl-zbi2-pg-en.pdf), `^XA`, `^XZ`, `^PW`, `^LL`, `^FO`, `^A`, `^FD`, `^FS`, `^GB`, `^BY`, `^BC` and `^BQ`; command sections are indexed in [the reference index](../docs/zpl-command-index.tsv).

| Operation | Included | Excluded / caveat |
| --- | --- | --- |
| `parse` | New parser/engine, entire input consumed, output materialized as the API requires, consumed and released | No serialization or validation pass; codyps/zpl frames borrowed commands, toolchain/ZPLr build an AST, labelize/BinaryKits/Go build label objects, forge also constructs render instructions. Not equivalent semantics. |
| `png` | New document/parser state, render, PNG encode to in-memory bytes, release output | No input-file read or output-file write inside timing; native encoding, font and antialiasing defaults differ. |
| `generate` | New builder, format and add 1 or 48 `Item NN` text fields, serialize ZPL | No parsing/rendering/network; equivalent text-count and coordinate workload, not identical ZPL or font layout. |

Source API references: [codyps/zpl](https://github.com/codyps/zpl/blob/280fc0cf4d0a49c916463d936e4307a2a226928e/zpl/src/lib.rs), [toolchain](https://docs.rs/zpl_toolchain_core/0.4.1/zpl_toolchain_core/), [labelize](https://docs.rs/labelize/1.6.0/labelize/), [forge](https://docs.rs/zpl-forge/0.3.2/zpl_forge/), [builder](https://docs.rs/zpl-builder/0.1.0/zpl_builder/), [Rust FFI](https://docs.rs/crate/zpl-rs/0.1.8), [Go](https://github.com/StirlingMarketingGroup/go-zpl), [BinaryKits](https://github.com/BinaryKits/BinaryKits.Zpl), [Python](https://github.com/cod3monk/zpl), [JSZPL](https://github.com/DanieLeeuwner/JSZPL), [ZPLr](https://github.com/le2ni/zplr). Versioned source commits are in the source lock; external library implementation is not copied into this project.

## Timing and memory

One calibration process estimates a batch count targeting 200 ms, capped at one million operations. Five independent processes measure that fixed batch. Every process warms for at least 250 ms and three operations; input loading and warm-up are excluded from its monotonic-clock timer. A stable seeded shuffle orders cells; the orchestrator runs one child at a time. Rust uses `black_box`; other adapters retain/consume outputs through checksums or runtime liveness barriers. No forced garbage collection or custom allocators. Node API calls are awaited, so promise scheduling overhead is included. JIT/GC can still affect results; inspect the min–max batch spread.

Each sample is a batch average. The reported median and min–max are **not per-label tail latencies** or confidence intervals. Process elapsed time including startup is recorded separately in raw JSON, but is not the headline latency. Memory is measured separately with equal operation counts across libraries; timing calibration does not determine the memory workload. Native worker-thread counts and runtime scheduling use library defaults; this is wall-clock latency, not CPU-normalized throughput. No CPU affinity, frequency locking or cache flush is applied.

Memory runs use three warm-up operations, ten measured operations (configurable with `--memory-iterations`), and one output capture. No forced GC is applied. A freshly executed, small native launcher forks the adapter and uses `wait4` to collect that adapter's `ru_maxrss`: bytes on macOS, KiB converted to bytes on Linux. This excludes the Python controller's pre-exec resident memory, which otherwise creates an artificial floor for small adapters on Linux. The launcher itself is not included. Startup, runtime/JIT, warm-up, operations and output capture are included. Five independent memory samples are retained separately from timing samples; charts show their median peak RSS and tables show the min–max range. Kernel RSS accounting has finite resolution and runtime/GC behavior still varies; this is process footprint, not an exact allocation count, retained heap, or concurrent-server estimate. Child runs have a 90-second timeout and failures are retained with diagnostics. Historical schema-1 results used the maximum RSS of calibrated timing batches and are not directly comparable to this schema-2 memory protocol.


## Output checks

PNG files are fully decoded with Pillow and must be 400×300 with both dark/light pixels after alpha compositing onto white. Boxes are also compared to a hand-defined inward-border mask: a 100×60 box at (20,20) with thickness 4 and an 80×80 filled box at (180,100). Pixel differences are reported, never silently corrected. Generated ZPL must contain the expected framing, field count and every `Item NN` value. Parser completion is only an API smoke check, not semantic parity. No library is used as another's correctness oracle.

Captured samples make differences inspectable. Text shape, barcode decoding, binary downloads, malformed-input behavior, full command coverage and real-printer fidelity are **not** established by these five fixtures. Those remain selection criteria in [capabilities](https://codyps.github.io/zpl-comparison/examination.html) and the repository's separate conformance tests.

## Code-size accounting

`run.py:source_sizes` defines the selected implementation roots. Counts include `.rs`, `.go`, `.cs`, `.ts` and `.py` source, comments, Rust tests inside `src` (including `test.rs`) and generated tables. Files named `*_test.*`, `*.test.*`, `*.spec.*` and tooling/example trees are excluded. No SLOC equivalence claim is made. codyps/zpl includes `zpl/src` and `raster-diff/src`; toolchain includes its four supporting core/profile/diagnostic/table crates. Other Rust source counts use the actual resolved registry package. Go includes its library/render tree; FFI adds the Rust wrapper. BinaryKits includes Viewer and Label. Node includes each project's pinned `src`; Python includes `zpl/`. Fonts, binaries and third-party dependency source are excluded. These selected trees sometimes contain supporting APIs not exercised by the benchmark.

Deployment sizes include the adapter plus linked/deployed dependencies: stripped release executable for Rust/Go, plus source-built Go shared library for FFI; .NET publish directory; Node runtime dependency closure including Skia for ZPLr; Python package plus Pillow. System libraries and the shared Node/Python/.NET runtime installation are excluded. Assets embedded into a binary are included. These are **deployment bytes**, not machine-code text-section bytes. The .NET publish directory includes its packaged platform-native assets. The JSON records exact file manifests/hashes; source and deployment totals have intentionally different boundaries.

## Regenerate / test the harness

To generate reports in Bazel's output tree without modifying the checkout:

```sh
bazelisk build //:reports
```

Open `bazel-bin/reports/README.md` or
`bazel-bin/reports/docs/benchmarks/README.md`. The output includes collected
evidence and maintained documentation at their original relative paths so report
links and images remain usable. The default target compiles each local renderer
and generates each case/library image locally. It also runs the invalid-input
probes and extracts command support from the selected sources. Printer previews
and Labelary responses remain saved evidence; this build never contacts a printer
or rendering service.

Bazel caches each library deployment (including the Go shared library used by
FFI), each case/library render, each printer comparison and difference PNG, each
metamorphic relation, each case viewport, each thumbnail, and each gallery page
independently. Summary plots, report families, and final tree assembly are separate actions.
The accuracy overview includes all four corpora and every category, with per-case
IoU/status tables, scored denominators, difference-image counts, and separate
metamorphic equality results. All tested cases have full pages under
`docs/benchmarks/accuracy/comparisons/cases/`; additional corpora use
`conformance-`, `external-zpl-`, or `layout-accuracy-` filename prefixes to avoid
collisions. Existing nested gallery URLs remain available. Assembly validates
that every comparison has a linked case page, renderer section, and all expected
render/difference images before CI can publish the tree.
Image actions use Bazel Python workers to reuse interpreter startup while retaining
separate cache keys. Report renders also reuse Node and .NET adapter processes,
with fresh per-request parser/printer/font configuration. Each Python worker keeps
at most five adapters and retires each after 128 requests to bound runtime heap
growth. Errors discard the process and use the one-shot adapter for the original
diagnostic; timeouts kill the process group within the same request time budget.
Performance measurements and invalid-input probes continue to use fresh processes. An
unchanged build executes none of these actions. A printer-reference change does
not recompile a library or rerender local images. A library change rerenders its
own cases; unrelated libraries remain cached. Shared viewport changes can refresh
other thumbnails for that case, because their common crop must remain consistent.

CI restores the most recent action-cache snapshot and saves a new immutable
snapshot for every main-branch run, including fixture-only changes. A GitHub
restore-key match is expected; Bazel's own disk-cache hit counts establish which
actions were reused. The older BUILD/MODULE-keyed cache stopped saving on exact
hits, so new fixture results could be rebuilt on every runner. Main builds now
finish instead of cancelling one another before cache upload; superseded PR
builds may still be cancelled. Successful main runs publish GitHub Pages and
retain immutable observation bundles as release assets.

`//:render_libraries` builds the adapters before image generation and checkpoints
their cache separately. Both completed and partially completed report actions
are saved on build failure, with step timeouts leaving room for that save.

The same `//:reports` CI build includes the [font-free layout suite](../test-data/layout-accuracy/README.md):
20 cases across ten local renderer adapters plus saved Labelary responses, with saved ZD621 references, difference
images and a separate gallery/summary. CI verifies all 160 render/comparison
pairs and their printer-reference dependencies. Build only its images and gallery
with `--output_groups=suite_layout-accuracy`; fork CI reproduces its saved evidence
through `//:reports_saved`. Labelary is replayed offline from checked-in captures.
The `build-performance` Actions artifact contains separate library/report Bazel
profiles and build-event logs for checking cache reuse and execution costs.
Generated renders use one lossless grayscale encode; difference PNGs use the
exact four-color palette. Compression and palette encoding do not change pixels,
comparison scores, full-canvas dimensions, or original printer/service captures.

Dependencies are fetched during repository resolution. Rust, Go, Node, .NET, and
Python toolchains are pinned; native toolchain archive hashes are in
`build/toolchains.lock.json`. Cargo, Go, npm, and NuGet dependencies retain their
lockfile integrity checks. Compilation runs offline against declared downloaded
inputs. A C compiler/system SDK, Git, curl, and Python 3.11+ are bootstrap
prerequisites. Native build actions use the host C compiler and SDK, whose
platform/version identity participates in the cache key; native compilation is
local execution, not a remote-execution toolchain.
Go compilation excludes the download phase's user-home files and checksum
database bookkeeping, including its moving `latest` checkpoint. Downloads still
verify `go.sum`; those network-verification files are unused by the offline build
and must not invalidate otherwise identical library actions.

For the private `codyps/zpl` source, configure Git access or point Bazel at a
checkout containing the pinned commit:

```sh
bazelisk build //:reports --repo_env=ZPL_SOURCE_PATH=/absolute/path/to/zpl
```

Bazel fetches exactly the locked commit from that repository into its own input
tree; uncommitted files in the source checkout are not used. Individual native
builds are available as `//:library_codyps-zpl`, `//:library_go`, etc., or all
rendering libraries as `//:libraries`. To build just one comparison case and its
images/pages, use an output group, for example:

```sh
bazelisk build //:reports --output_groups=case_accuracy_argument-font0-height-16
```

`bazelisk build //:reports_saved` builds a fork/offline preview without native
compilation. It downloads the immutable archive pinned in
[`build/baseline.lock.json`](../build/baseline.lock.json), or a selected CI bundle,
and imports observations independently. Each replay must match the source bytes,
requested canvas, device profile, and adapter/source/dependency input identity.
Missing or changed observations are **not measured**, with no image or score.
A corrupt successful observation fails the build. Original observation times and
deployment hashes are retained; report generation does not create a new measurement.

New fixtures require their source definitions and appropriate external-reference
metadata. Local renderer snapshots never need to be committed. Trusted CI measures
the new cases; fork previews show unavailable observations until a compatible
trusted bundle exists. Labelary responses are replayed directly from the canonical
capture archive, with missing responses explicitly unavailable.

The `Comparison site` workflow runs on pull requests, main pushes, manual dispatch,
and a daily schedule. Trusted runs resolve the selected sources and build local
observations; main publication follows the current private renderer main revision.
Fork runs resolve a published `ci-observations-*` release to a concrete URL and
SHA-256 before building. The initial archive remains the fallback before the first
release is published. It is historical evidence and lacks current input identities,
so its local render rows remain unavailable in current comparisons.

Successful main runs publish the site through GitHub Pages and retain observation
bundles as release assets. Those releases have no artifact-expiration deadline.
The seven-day Actions artifact transfers the bundle to the publication job; it is
not the durable copy. The build job retains read-only repository permissions; only
the main-only publication job can create releases. Each release uses a unique run
and attempt tag and contains the archive plus its hash/identity manifest. Do not
remove releases still used by replay locks.

To select a current bundle locally, with the GitHub CLI configured:

```sh
mkdir -p benchmarks/_work
python3 .github/scripts/fetch_baseline.py --repository codyps/zpl-comparison --output "$PWD/benchmarks/_work/baseline.lock.json"
bazelisk build //:reports_saved --repo_env=ZPL_BASELINE_LOCK="$PWD/benchmarks/_work/baseline.lock.json"
```

Keep the resolved lock to reproduce that exact preview. Bazel's repository cache
supports subsequent offline replay. The same case and suite output groups work
with live and saved targets. Additional groups are `suite_invalid`, `suite_support`,
`suite_public`, and `suite_paired`.

| Inputs retained in source | CI-owned results |
| --- | --- |
| Fixture definitions, adapters, source/dependency/toolchain pins | Local PNGs, statuses, diagnostics, deployment identities |
| Valid/invalid fixture pairs and probe contracts | Two repetitions of each input across the ten built adapters' 18 API lanes; classifications and report |
| Resolved source/package trees and maintained argument notes | Extracted command support, inventory and compatibility pages |
| Exact printer/SaaS captures, submitted bytes, settings and provenance | Comparisons, relations, scores, differences, thumbnails and galleries |
| Public-label fixtures and paired printer captures | Current public-document and ZQ610/ZD621 profile evaluations |
| Pinned barcode decoder and input images | Decoder evidence with input hashes; decoding does not establish pixel parity |
| Current comparison rows | Total-failure JSON and TSV; unavailable observations are unscored |
| Capability template and selected repositories | Timestamped GitHub popularity data on main/scheduled runs; API failures stay unavailable |
| Performance workloads and built adapters | Fresh uncached timings and memory measurements on each trusted run |

Renderer and probe actions are cached on their declared inputs. Changing reporting
code recomputes reports without rerunning adapters. Source support is extracted
from the resolved source/package trees on trusted builds; saved previews explicitly
retain the baseline's source revisions. Performance timings always run outside the
action cache. Independent decoder checks run offline using the pinned dependency.

Fixture manifests and case bytes still define the analysis graph. After editing a
generator, run it and include the updated manifest/cases; CI verifies byte equality.
Coverage catalogs are generated in the output tree. Captured historical corpus
manifests and exact submitted ZPL stay unchanged as external-evidence provenance.
No printer or rendering-service request occurs in the build.

Raw external captures, imported sources/licenses, fonts, lockfiles, fixture
specifications and authored findings remain repository inputs. Local renderer
observations, computed JSON/TSV, coverage catalogs, plots, diffs and generated pages
are ignored build outputs. Historical authored findings link to the original Git
revision. The pre-migration archive preserves the removed historical snapshots.

The Bazel and Python versions are pinned. Update Python dependencies with:

```sh
uv pip compile benchmarks/requirements.txt --python-version 3.13 --generate-hashes -o build/requirements.lock.txt
```

Keep `MODULE.bazel.lock` checked in. To inspect cache behavior, use
`bazelisk build //:reports --explain=/tmp/zpl-reports-explain.log --verbose_explanations`.
The legacy `benchmarks/regenerate.py --measure` and `benchmarks/accuracy/regenerate.py`
commands remain available for manual measurements, including generator-only
libraries outside the CI renderer set. Their outputs belong in ignored work
folders or archived observation bundles, not the source branch.

```sh
benchmarks/_work/venv/bin/python -m unittest discover -s benchmarks -p 'test_*.py'
cargo fmt --manifest-path benchmarks/adapters/rust/Cargo.toml -- --check
```

Static SVG plots and relative image links render directly in GitHub Markdown; no Pages service or JavaScript is required.

## Labelary renderer captures

Labelary is included in the printer-accuracy matrix as an additional renderer.
[Capture provenance and original PNGs](https://codyps.github.io/zpl-comparison/methodology.html)
record UTC timestamps when the service exposes no build version. Tests replay
these responses offline; the ZD621 captures remain the correctness baseline.
See [capture and refresh commands](accuracy/README.md#labelary-renderer).

## Generate the compatibility reference

[Browse by library, command or feature](https://codyps.github.io/zpl-comparison/examination.html). These
GitHub Markdown pages use checked-in source evidence, argument notes, printer
measurements and the conformance manifest. Saved conformance execution results
are included when `docs/benchmarks/conformance/results.json` exists.

```sh
bazelisk build //:reports_saved
```

The saved-report target regenerates and checks compatibility pages inside its
output tree without rebuilding libraries or contacting a printer. To refresh evidence, build the adapters, run
`support.py`, the accuracy suite, and optionally `conformance.py --output
docs/benchmarks/conformance`, then regenerate. CI builds the Bazel report tree and publishes successful `main` builds to `generated`.
Source and renderer measurements remain separate, dated evidence.

### Feature renders and printer differences

The repository-wide command rebuilds feature and external galleries from saved results.
With `--measure`, it also runs all feature fixtures through all configured renderers.
The narrower accuracy command accepts `--reports-only` to rebuild accuracy pages and
differences offline from saved render results and checked-in printer captures. Renderer crashes/timeouts remain failures after the
reports are preserved; they do not prevent the remaining fixtures from running.

```sh
benchmarks/_work/venv/bin/python benchmarks/accuracy/regenerate.py --reports-only
benchmarks/_work/venv/bin/python benchmarks/accuracy/features.py --check
```

To deliberately collect new references, use an unused output directory:

```sh
benchmarks/_work/venv/bin/python benchmarks/accuracy/capture.py \
  --host http://d7j211001302.bed.einic.org/ \
  --corpus test-data/render-conformance \
  --skip encoding-29 --skip encoding-30 \
  --skip-reason "Previous ZD621 preview timeouts; avoid disrupting shared use" \
  --output benchmarks/_work/new-feature-references
```

This uses Preview Label, never physical printing. Captures identify printer model,
firmware, timestamp, source/image hashes, and a repeated control. Missing previews
are recorded as unavailable and never assigned a correctness score. Interrupted
captures can use `--resume`; `--skip NAME --skip-reason TEXT` records a known
problematic fixture without resubmitting it. A timeout pauses for 30 seconds before checking recovery, up to four times by default (`--recovery-attempts` changes this); a timed-out POST is never immediately replayed. If the printer recovers, that fixture is recorded as unavailable and capture continues; otherwise capture stops resumably. `--interval`, `--cooldown`, and `--object-name` control pacing and the dedicated RAM object. Only a completed capture with a matching repeated control is
accepted for accuracy. Review a new capture before replacing
`benchmarks/accuracy/conformance-reference`.

On the ZD621 with firmware V93.21.33Z, `encoding-29` and `encoding-30` have timed out during preview. The example excludes them from printer submission and records them as unavailable; they still run through all offline renderers.

Inputs containing literal NUL bytes are also recorded as unavailable without HTTP submission after `raster-equivalent-binary` timed out on the shared printer. Their unmodified inputs still run in the offline renderer suite.

Gallery previews share a common origin and remove trailing blank space, then scale
to at most 360 × 160 pixels. Each preview links to its full-size PNG; cropping and
scaling never affect IoU. The same gallery covers the feature corpus and external
examples, with explicit unscored reasons for inputs that cannot be sent to a printer.

The 24 compact fixtures use 640 × 320-dot canvases. Their source links identify the
codyps/zpl regression tests that inspired them; they are development cases, not an
independent holdout. Original comparison-library version pins remain unchanged.

To add fixtures without recapturing existing inputs, use `capture.py --extend`
with the existing complete printer capture directory and expanded corpus. It
verifies every retained source/image hash and captures a new repeated control.
`labelary.py --extend` similarly captures only newly added service inputs, preserving
all earlier response bytes and per-request timestamps. Changed or removed inputs
require a new snapshot. Run the full accuracy regeneration afterward.
