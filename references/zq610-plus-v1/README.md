# ZQ610 Plus / ZD621 paired previews

All 116 cases have captures from both printers: 60 barcode formats, 37
layout/font/canvas controls, three unclipped text replacements, and 12 width
boundary controls, and four visible clipping-control companions. The [gallery](../../docs/benchmarks/zq610-plus/index.html)
contains native PNGs, exact submissions, local output and directional diffs.
Both report targets rebuild it offline from this saved evidence.

CODABLOCK A moves x=60 to x=20; inverted A/D/E text replacements move x=300
to x=20. Payloads, module sizes and fonts remain unchanged. Native images are
never edited. Deliberate clipping diagnostics are separately identified.

Each printer has 112 nonblank exact local comparisons, one expected blank
clipping diagnostic, and three rotated Font 0 residuals: B under/over 1/3,
I 5/3, R 5/0 (foreground IoU 0.9854–0.9926). These differences are shared by
both printers. All 60 barcodes and three text replacements match locally.
113 pairs match in the explicitly cropped common coordinate region; the
other three are width-cap controls (400, 385, 800). Local accuracy compares
entire native canvases without padding, cropping, alignment or scaling.

ZQ610 V100.21.21Z retains 2030 preview rows despite shorter LL and caps width
at 384. Both printers round width to multiples of 64, shift the origin by
floor((rounded - requested) / 2), and fix canvas width at the first draw.
Ink can extend into the rounded padding. The ZQ610 profile enables four
independent options. ZD621 local comparisons use `zd621-preview`, enabling
width rounding and latching on the ZD621 base. The library default is unchanged.

This focused corpus is not the entire historical 5,106-record replayable
inventory. Results concern these HTTP previews, not physical prints, decoder
success, arbitrary fonts or other firmware/configurations.

## Provenance and recovery

`manifest.json` records identity, firmware, URL, UTC sessions/requests, source
commits, tool hashes/snapshots, exact ZPL, HTML, status pages, image hashes,
dimensions and ink bounds. All recorded files are verified before reporting
or resuming. `analysis.json` hashes the manifest and saved local PNGs.

Two ZQ610 sessions stalled during EAN-8 and rotated Font E. Failed attempts
and sessions without end controls remain recorded; explicit retries succeeded.
A user power cycle and authorized remote resets recovered service. Later
batches were bounded to 20 cases with repeated controls. These do not
retroactively make earlier incomplete sessions pass repeatability checks.
The restart action verifies serial and records the reset; capture does not
silently restart. Use one capture process at a time.

## Reproduce

Python 3 with Pillow and the sibling zpl checkout are required for new captures
and local rendering. Build the `zpl-to-svg` example first.

```sh
cargo build --manifest-path ../zpl/Cargo.toml --locked -p zpl --example zpl-to-svg
python benchmarks/zq610.py prepare --output /tmp/new-zq610-campaign
python benchmarks/zq610.py add-fit-controls --output /tmp/new-zq610-campaign
python benchmarks/zq610.py add-width-controls --output /tmp/new-zq610-campaign
python benchmarks/zq610.py add-clipping-controls --output /tmp/new-zq610-campaign
python benchmarks/zq610.py capture --output /tmp/new-zq610-campaign --printer zq610 --interval 1 --max-cases 20
python benchmarks/zq610.py capture --output /tmp/new-zq610-campaign --printer zd621 --interval 1 --max-cases 20
```

Repeat bounded capture commands for unattempted cases. Use `--retry-case CASE`
for deliberate retries; prior attempts remain recorded. Then run:

```sh
python benchmarks/zq610.py report --output /tmp/new-zq610-campaign --profile zq610-plus
python benchmarks/zq610_pages.py
```

The last command rebuilds pages from the saved default reference directory
without a printer or renderer. `export-tests` includes four original smoke
frames; `--extend-tests` verifies existing source/PNG hashes and refuses native
reference replacement. It pins directional errors and local pixel hashes;
only the reviewed three text residuals and explicit blank diagnostic are
accepted alongside exact results. Existing ZD621 baselines are preserved.
