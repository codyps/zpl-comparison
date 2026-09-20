# Repeatable ZPL library comparison

**[Read the GitHub-rendered report, plots and tables](../docs/benchmarks/README.md).**
The root README links to these detailed reports. [Library capabilities and selection](../docs/benchmarks/capabilities.md) distinguish parsers, renderers and generators.

[Command/argument inventory](../docs/benchmarks/command-support.md) and [printer accuracy reproduction](accuracy/README.md) extend the comparison with offline captured references.

[Invalid-ZPL rejection tests](invalid/README.md) run paired valid/invalid inputs across parser and renderer APIs, with repeated executions and explicit error/crash classification.

The [rendering conformance corpus](../test-data/render-conformance/README.md) adds 531 focused and combined test files. Its [shared accuracy gallery](../docs/benchmarks/accuracy/comparisons/features/README.md) shows each printer preview alongside all eight renderer outputs and pixel differences. Invalid inputs run offline only. Feature scores are reported separately from the argument/barcode chart because the sampling differs.

The [external label corpus](../test-data/external-zpl/README.md) adds eight unchanged,
pinned upstream examples. [Execution report](../docs/benchmarks/external-zpl/README.md).
Regenerate its images, JSON and Markdown with:

```sh
benchmarks/_work/venv/bin/python benchmarks/conformance.py --corpus test-data/external-zpl --only all --output docs/benchmarks/external-zpl
```

## Run

Supported hosts: Linux and macOS. Install Rust/Cargo, Go ≥1.25, Node ≥22 with npm, .NET SDK 8, Python ≥3.12, Git and a native C toolchain. Build tools download dependencies; measured operations never contact a rendering service or printer. Use an idle machine and avoid concurrent builds while measuring.

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

The saved measurements are actual local runs. CPU/toolchain/OS metadata is in the report and JSON. CI builds the offline reports with Bazel from this collected evidence. Successful builds of `main` automatically publish the complete output tree to the independent [`generated` branch](https://github.com/codyps/zpl-comparison/tree/generated). CI does not collect new measurements or contact printers or rendering services.

## Pins

- [`sources.lock.json`](sources.lock.json): immutable source commits for the Go engine, Python package and source-size survey. Git checkouts must be clean when changing revisions.
- [`adapters/rust/Cargo.lock`](adapters/rust/Cargo.lock): exact Rust dependency graph. Each binary is built separately with one feature; `--all-features` is **not** a supported build. codyps/zpl and its raster dependency are path dependencies.
- [`adapters/node/package-lock.json`](adapters/node/package-lock.json): exact Node package graph and integrity hashes; `npm ci`. The pinned `skia-canvas` installer supplies its native component.
- [`adapters/go/go.mod`](adapters/go/go.mod) / [`go.sum`](adapters/go/go.sum): direct Go adapter; engine source also pins its own module graph. `-mod=readonly` is used for builds. The Rust wrapper's `LIBZPL_PATH` points at this source-built Go shared library.
- [`adapters/dotnet/packages.lock.json`](adapters/dotnet/packages.lock.json): exact NuGet graph and content hashes; locked restore. .NET is framework-dependent.
- [`requirements.txt`](requirements.txt): Python plotting/PNG decoder versions; these are outside timed operations except Pillow's import in the Python builder. Transitive plotting packages can vary without changing the timed benchmark contract.

Update pins explicitly, regenerate dependency locks using the relevant package manager, inspect API changes, then rebuild and rerun. Never compare two reports without checking their host, versions, fixtures and lock hashes. The JSON includes hashes of actual measured codyps/zpl source files so an uncommitted source change remains identifiable.

## Workloads and API boundaries

All renderer inputs are the same checked-in, single-label, ASCII ZPL bytes, at **400×300 dots**, nominal 203 DPI / 8 dots per mm. No implicit default-size comparison. Fixtures exercise boxes, one font-0 text field, Code 128, QR, and 48 small text fields. The explicit dimensions make nominal 203-versus-203.2 DPI immaterial to the canvas size. Fixtures reference the bundled [Zebra Programming Guide](../docs/zpl-zbi2-pg-en.pdf), `^XA`, `^XZ`, `^PW`, `^LL`, `^FO`, `^A`, `^FD`, `^FS`, `^GB`, `^BY`, `^BC` and `^BQ`; command sections are indexed in [the reference index](../docs/zpl-command-index.tsv).

| Operation | Included | Excluded / caveat |
| --- | --- | --- |
| `parse` | New parser/engine, entire input consumed, output materialized as the API requires, consumed and released | No serialization or validation pass; codyps/zpl frames borrowed commands, toolchain/ZPLr build an AST, labelize/BinaryKits/Go build label objects, forge also constructs render instructions. Not equivalent semantics. |
| `png` | New document/parser state, render, PNG encode to in-memory bytes, release output | No input-file read or output-file write inside timing; native encoding, font and antialiasing defaults differ. |
| `generate` | New builder, format and add 1 or 48 `Item NN` text fields, serialize ZPL | No parsing/rendering/network; equivalent text-count and coordinate workload, not identical ZPL or font layout. |

Source API references: [codyps/zpl](https://github.com/codyps/zpl/blob/280fc0cf4d0a49c916463d936e4307a2a226928e/zpl/src/lib.rs), [toolchain](https://docs.rs/zpl_toolchain_core/0.4.1/zpl_toolchain_core/), [labelize](https://docs.rs/labelize/1.5.0/labelize/), [forge](https://docs.rs/zpl-forge/0.3.2/zpl_forge/), [builder](https://docs.rs/zpl-builder/0.1.0/zpl_builder/), [Rust FFI](https://docs.rs/crate/zpl-rs/0.1.8), [Go](https://github.com/StirlingMarketingGroup/go-zpl), [BinaryKits](https://github.com/BinaryKits/BinaryKits.Zpl), [Python](https://github.com/cod3monk/zpl), [JSZPL](https://github.com/DanieLeeuwner/JSZPL), [ZPLr](https://github.com/le2ni/zplr). Versioned source commits are in the source lock; external library implementation is not copied into this project.

## Timing and memory

One calibration process estimates a batch count targeting 200 ms, capped at one million operations. Five independent processes measure that fixed batch. Every process warms for at least 250 ms and three operations; input loading and warm-up are excluded from its monotonic-clock timer. A stable seeded shuffle orders cells; the orchestrator runs one child at a time. Rust uses `black_box`; other adapters retain/consume outputs through checksums or runtime liveness barriers. No forced garbage collection or custom allocators. Node API calls are awaited, so promise scheduling overhead is included. JIT/GC can still affect results; inspect the min–max batch spread.

Each sample is a batch average. The reported median and min–max are **not per-label tail latencies** or confidence intervals. Process elapsed time including startup is recorded separately in raw JSON, but is not the headline latency. Calibration iterations differ across libraries, so peak memory reflects different batch lengths; use `--iterations N` if investigating that effect rather than treating RSS as per-operation allocation. Native worker-thread counts and runtime scheduling use library defaults; this is wall-clock latency, not CPU-normalized throughput. No CPU affinity, frequency locking or cache flush is applied.

`os.wait4` collects **the specific child's** `ru_maxrss`: bytes on macOS, KiB converted to bytes on Linux. It includes startup, runtime/JIT, warm-up, operation batches and one captured output. Five samples use five fresh children. Maximum RSS across samples is shown; it is not a parent-process cumulative high-water mark, allocation count, retained heap, or concurrent-server estimate. Child runs have a 90-second timeout and failures are retained with diagnostics.

## Output checks

PNG files are fully decoded with Pillow and must be 400×300 with both dark/light pixels after alpha compositing onto white. Boxes are also compared to a hand-defined inward-border mask: a 100×60 box at (20,20) with thickness 4 and an 80×80 filled box at (180,100). Pixel differences are reported, never silently corrected. Generated ZPL must contain the expected framing, field count and every `Item NN` value. Parser completion is only an API smoke check, not semantic parity. No library is used as another's correctness oracle.

Captured samples make differences inspectable. Text shape, barcode decoding, binary downloads, malformed-input behavior, full command coverage and real-printer fidelity are **not** established by these five fixtures. Those remain selection criteria in [capabilities](../docs/benchmarks/capabilities.md) and the repository's separate conformance tests.

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
links and images remain usable. Bazel downloads the pinned Python interpreter
and locked Python dependencies on the first build; report generation itself is
offline and needs no prepared adapters or local virtualenv.

The whole offline pipeline is currently one cached action. An unchanged build
skips generation; changing declared evidence, generator code, or its toolchain
rebuilds the report tree. Missing outputs are rebuilt. Generated Markdown, plots,
differences, thumbnails and fixture outputs in the checkout are not build inputs.
This does not yet provide per-case or per-report incremental generation.
Measurements and printer/service captures remain explicit collection operations;
the Bazel target consumes their saved results and never refreshes them.

The Bazel version is pinned in `.bazelversion`; Python and `rules_python` are pinned
in `MODULE.bazel`. After changing `benchmarks/requirements.txt`, update the full
dependency lock with:

```sh
uv pip compile benchmarks/requirements.txt --python-version 3.13 --generate-hashes -o build/requirements.lock.txt
```

Keep `MODULE.bazel.lock` checked in. Bazel outputs and downloaded dependencies are
not checked into the source branch. To inspect why an action runs, use
`bazelisk build //:reports --explain=/tmp/zpl-reports-explain.log --verbose_explanations`.

The `Generated reports` workflow builds this target on pull requests, pushes to
`main`, and manual dispatch. Only successful `main` runs publish. The first
publication creates an orphan root commit on `generated`; subsequent publications
append to that branch's own history without force pushes or merging `main`.
Identical output creates no new commit, and a build whose source revision is no
longer the tip of `main` is skipped. Publication replaces the complete snapshot,
including removing obsolete files, and records the source commit and CI run in
the commit message. An intermediate artifact transfers the tree between the
read-only build job and the publishing job; the branch is the published result.
Bazel dependency and action caches are reused across CI runs.

Regenerate **all derived resources** from the checked-in collected evidence:

```sh
benchmarks/_work/venv/bin/python benchmarks/regenerate.py
```

This includes `docs/benchmarks/accuracy/accuracy.svg` (the chart embedded near the top of the repository README), its PNG, every other plot, generated Markdown, difference PNGs, thumbnails and compatibility pages. No adapters, source checkouts, Cargo metadata, printer or network service are required for this default mode; install the Python requirements first. Saved measurements and capture dates are preserved. Missing or inconsistent input evidence fails the command rather than producing invented results.

| Collected or maintained input | Regenerated resources |
| --- | --- |
| Render-conformance and invalid-input fixture definitions | ZPL fixtures, manifests and generated coverage catalog |
| `docs/benchmarks/results.json` | Performance, memory and size SVG/PNG plots and benchmark README |
| Popularity snapshot, dependency locks, pinned revisions and maintained capability template | Capabilities survey and complete popularity table |
| `docs/benchmarks/command-support.json` and command index | Command-support Markdown inventory |
| `docs/benchmarks/invalid/results.json` | Invalid-input report |
| Labelary capture manifest and original response images | Service capture report |
| Accuracy results, original library renders and printer captures | Accuracy SVG/PNG, report, argument matrix, full-size differences, compact thumbnails and case/library pages |
| Feature/external results, original renders and printer captures | Execution reports, computed accuracy JSON, full-size differences, compact thumbnails and case/library pages |
| Saved support evidence, measurements, corpus and maintained argument notes | Compatibility library/command/feature pages and input hashes |

Raw renderer samples, imported examples/licenses, printer captures, Labelary responses and measurement JSON are collected evidence, not synthesized reports. Argument notes, the capabilities template (`benchmarks/templates/capabilities.md`), the command index, provenance documents and source-inspiration notes are maintained inputs. The command composes the published outputs from these inputs; it does not replace them with new measurements or downloads.

To collect fresh local measurements **and** rebuild everything, after preparing all adapters:

```sh
benchmarks/_work/venv/bin/python benchmarks/regenerate.py --measure
```

This refreshes source-support evidence, performance, invalid-input behavior, original accuracy, features and external examples. Printer and SaaS captures use the explicit collection commands below. A runner failure with no fresh saved result stops regeneration; recorded crashes/timeouts are published and cause a nonzero exit after reports are rebuilt.

The command writes local files. The GitHub raw URL and README change when those files are committed and pushed; it does not publish commits automatically. The narrower `benchmarks/accuracy/regenerate.py` remains available for accuracy-only work.

```sh
benchmarks/_work/venv/bin/python -m unittest discover -s benchmarks -p 'test_*.py'
cargo fmt --manifest-path benchmarks/adapters/rust/Cargo.toml -- --check
```

Static SVG plots and relative image links render directly in GitHub Markdown; no Pages service or JavaScript is required.

## Labelary renderer captures

Labelary is included in the printer-accuracy matrix as an additional renderer.
[Capture provenance and original PNGs](../docs/benchmarks/labelary/README.md)
record UTC timestamps when the service exposes no build version. Tests replay
these responses offline; the ZD621 captures remain the correctness baseline.
See [capture and refresh commands](accuracy/README.md#labelary-renderer).

## Generate the compatibility reference

[Browse by library, command or feature](../docs/compatibility/README.md). These
GitHub Markdown pages use checked-in source evidence, argument notes, printer
measurements and the conformance manifest. Saved conformance execution results
are included when `docs/benchmarks/conformance/results.json` exists.

```sh
python3 benchmarks/compatibility.py
python3 benchmarks/compatibility.py --check
```

Generation needs only Python 3.12+ and the checkout; it does not rebuild libraries,
fetch dependencies or contact a printer. `--check` verifies generated bytes and
rejects stale generated pages. To refresh evidence, build the adapters, run
`support.py`, the accuracy suite, and optionally `conformance.py --output
docs/benchmarks/conformance`, then regenerate. CI checks the published snapshot
before measurement and generates an updated snapshot afterward for its artifact.
Source and renderer measurements remain separate, dated evidence.

### Feature renders and printer differences

The repository-wide command rebuilds feature and external galleries from saved results.
With `--measure`, it also runs all feature fixtures through all eight renderers.
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
