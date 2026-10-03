# Public ZPL documents, October 2026

Twenty pinned public source documents yield 22 single-label comparison cases:
11 documents from [Labelixa](https://github.com/Labelixa/zpl-examples/tree/534ddba48d7597aa35df989ac31891f94c6f57a8/examples)
and nine from [BinaryKits](https://github.com/BinaryKits/BinaryKits.Zpl/tree/9d316458c33c90608859cc935d3ba1e0c7587be7/src/BinaryKits.Zpl.Viewer.WebApi/Labels/Example).
Both MIT licenses are retained in `licenses/`. `sources.json` records immutable
URLs, revisions, file/license hashes, dimensions, purpose, and exclusions.
`upstream/` preserves the downloaded bytes, including BOMs and whitespace.

[Measured results](../../docs/public-examples/README.md) ·
[Native-image gallery](../../docs/public-examples/index.html) ·
[Findings](../../docs/public-examples/FINDINGS.md) ·
[Capture manifest](../../references/public-zd621-20261002/manifest.json)

This campaign compares **all eleven registered renderers against the ZD621**.
The CI build measures every local renderer on all 22 inputs and replays the exact
saved Labelary responses. The site shows every renderer's output, difference,
status and provenance. Printer capture bytes remain the reference.

## Adaptations and scope

- Labelixa widths round up to a multiple of 64 dots, within 832 dots; explicit
  label lengths remain unchanged. The three-label batch is separated into three
  independent cases, not used to claim multi-label stream support.
- BinaryKits labels receive dimensions from their filename at 8 dots/mm,
  with width rounded up to a multiple of 64 dots. A leading UTF-8 BOM is removed.
- Coordinates, drawing commands, graphic bytes, fonts, barcode operands and
  payloads remain intact. Only whitespace outside the chosen format is normalized.
  Native images are not aligned, padded, cropped or rescaled for measurement.
- Literal `%s` and `{0}` placeholders, missing QR controls, missing field
  separators, and `^BY12` remain visible diagnostics. The cases are marked
  `boundary`, not certified valid. Printer acceptance alone does not prove the
  intended barcode payload was encoded correctly.
- BinaryKits Example1-54x86 has drawing commands below its requested canvas;
  that clipped material is not positive evidence of rendering support.
- Four other downloaded BinaryKits candidates were excluded: Example7 is wider
  than this printer and includes `^PR/^PQ`; Examples10–12 include font mapping,
  device/unit settings or quantity commands. See `sources.json`. Their commands
  were not sent to the printer. No font/object download or physical print was used.

Command definitions: Zebra ZPL Programming Guide, `^PW`, `^LL`, `^BQ`, `^B3`,
`^BY`, `^GF` and `^FS`, indexed in [the command index](../../docs/zpl-command-index.tsv).
The [Zebra command documentation](https://docs.zebra.com/us/en/printers/software/zpl-pg/zpl-commands.html)
and the pinned upstream files describe the commands; dot-level observations are
specific to ZD621-203dpi firmware V93.21.33Z.

## Reproduction

Install the Python dependencies in `benchmarks/requirements.txt` with Python 3.12+.
Offline fixture and saved-evidence checks:

```sh
python test-data/public-zpl/prepare.py --check
python benchmarks/labelary.py --check
python benchmarks/public_examples.py --check
python -m unittest discover -s site -p test_generate.py
```

To regenerate the complete matrix, run `bazel build //:reports` (or select
`--output_groups=suite_public`). `//:reports_saved` replays compatible observations
without executing renderers. The historical single-adapter measurement command
remains available for explicitly scoped codyps/zpl investigations:

```sh
python benchmarks/public_examples.py --renderer /path/to/codyps-zpl \
  --source ../zpl --output /tmp/public-zpl-new-measurement
```

The recorded run used the unchanged `main.rs` and `probe.rs` in
`benchmarks/adapters/rust/src`, copied into a temporary standalone Cargo package
with only `codyps-zpl = { package = "zpl", path = "/path/to/zpl/zpl", optional = true }`,
a `codyps-zpl` binary at `main.rs`, and the `codyps-zpl` required feature. Seed its
lockfile from the selected zpl workspace, then `cargo build --release --offline
--features codyps-zpl`. No renderer implementation was changed. `results.json`
records the source commit, working-tree status, every rendering source/asset hash,
adapter source and executable hashes, profile, and measurement time.

The comparison build executes all local adapters, validates the complete matrix,
and publishes the results. Hardware and Labelary captures are replayed offline
with their original dates and hashes.

Labelary's 22 responses were captured on 2026-10-02 with
`python benchmarks/labelary.py --extend`, preserving all 762 earlier observations.
That command explicitly submits only missing corpus inputs to the service.
Exact response PNGs, source/image hashes, HTTP metadata and request times are in
[the service manifest](../../docs/benchmarks/labelary/captures.json).
No renderer build version was exposed. The ZD621 remains the comparison reference;
Labelary's acceptance of an input does not certify its validity.

Regenerate the complete matrix with `bazel build //:reports`. The resulting
`results.json` records every renderer, its source identity, measurement time,
native comparison, and image hashes. `public_examples.py --reports-only` can
rebuild the tables and gallery from an existing assembled campaign without
executing renderers or contacting the service. Historical single-adapter reports
remain readable with their original measurement dates.

Captures are a separate, explicit operation. The recorded command was:

```sh
python benchmarks/accuracy/capture.py \
  --host http://D7J211001302.bed.einic.org/ \
  --corpus test-data/public-zpl --output references/public-zd621-20261002 \
  --object-name CMPPUB26 --interval 1 --cooldown 5 --recovery-attempts 1
```

The output directory must not already exist. The capture tool verifies the model,
firmware and source hashes, restricts submissions to its content-command allowlist,
applies its recorded inline state reset, and sends only HTTP Preview Label.
The last capture repeats the first label. All 23 returned images were nonblank;
the first and last pixels matched. Source, submission and PNG hashes are retained.

Optional independent barcode investigation uses temporary development tools
`zxing-cpp==3.1.1` and `Pillow==12.3.0`:

```sh
python benchmarks/audit_public_barcodes.py --check
```

It verifies the saved [decoded payload observations](../../docs/public-examples/barcodes.json).
Decoder failure is not proof of an invalid symbol. This dependency is not added
to core rendering or required for ordinary offline report checks.
