# Preview width audit, 2026-09-29

The generator previously changed 59 barcode-family sources from `^PW832` to
`^PW812`. The ZD621 rounds that width to 832 and centers the requested canvas,
shifting every field ten dots right. Ordinary comparisons now use the original
832-dot sources. Heights and field coordinates are unchanged.

`fresh-printer/` preserves a new 60-symbol preview batch with an identical
repeated control. The active conformance reference records its manifest hash
and adopts its 60 corresponding rows. Build validation checks the batch's
repeated control and every adopted row. Exact sources, submitted-request
hashes, original PNG bytes, device identity, and timestamps remain in the
batch manifest.

`printer/` independently preserves the earlier native-width batch collected on
2026-09-29 from 02:28:42Z through 02:33:38Z: 60 symbols, paired 812/832-dot
landmark controls, and an identical repeated control. Its exact corpus manifest
is `corpus-manifest.json`. All 60 newly captured symbol rasters match this
independent batch pixel-for-pixel.

Python and `/opt/local/bin/curl` could not access the local printer from the
capture environment; `/usr/bin/curl` succeeded. `capture_system_curl.py` records
the transport adapter used with the unchanged `capture.py` preview protocol,
inline reset, request bounds, and error handling. Reproduce from the repo root:

```sh
benchmarks/_work/venv/bin/python references/preview-width-audit-20260929/capture_system_curl.py \
  --host http://d7j211001302.bed.einic.org/ \
  --corpus test-data/render-conformance --group barcode-families \
  --output benchmarks/_work/new-native-width-printer
```

`comparison.json` compares the old and new printer captures. All 59 modified
sources have exactly the same pixels after accounting for the old ten-dot shift;
the already-native UPC-E case is unchanged. This shift check diagnoses the cause;
scoring still uses the original origin without aligning or editing either image.

All 60 Labelary barcode-family responses were freshly requested for the corrected
832x1218 canvases. `labelary-captures.json` retains request/response timestamps and
hashes; original response PNGs live in `docs/benchmarks/labelary/images/`.

Run `benchmarks/accuracy/audit_dimensions.py` to inventory every tracked ZPL file.
The audit checks every active conformance, external, and layout source, plus
current capture/import source copies. Unaligned exceptions are enumerated:

- Upstream originals and historical audit captures retain their exact bytes.
- ZQ610/ZD621 width-boundary and width-latching probes intentionally test rounding,
  clipping, and width caps; changing them would remove their test coverage.
- Performance and invalid-input probes use a local-only 400-dot canvas. They are
  never submitted for printer comparison, so preview rounding cannot bias them.

All 626 active manifest comparisons have widths divisible by 64. The 73 argument
probes and 60 archived barcode sources already use 832 dots. LL does not need
64-dot alignment on the ZD621; the ZQ610's retained 2030-row preview behavior is
part of its separate device diagnostics.

Every current ZD621 argument, conformance, layout, and external capture has
exactly its requested width and height, including their repeated controls.
