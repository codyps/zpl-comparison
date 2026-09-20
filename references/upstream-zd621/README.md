# Imported ZD621 reference controls

Imported from `codyps/zpl` commit
`de0676ae4a4b8728ed0ab75a18b112bae7cbe883` on 2026-09-20.
The source directories are `zpl/tests/fixtures/<collection>`.
Original ZPL, printer PNGs, capture notes, TSV manifests and per-case JSON are
preserved byte-for-byte. These are HTTP Preview Label responses from a ZD621
203-DPI printer running V93.21.33Z, not physical scans or renderer output.
See each collection's README for capture dates, initial state and limitations.
Upstream renderer-equality claims in those notes describe upstream tests; they
are not comparison measurements for the libraries in this repository.

The local manifest selects 67 additional execution cases from nine collections:

| Collection | Added coverage |
| --- | --- |
| databar-retail | UPC-E's four zero-suppression forms, invalid compressed/check-digit inputs, and retail module-width controls |
| barcode-defaults | Absent, empty and partial BY operands and retained barcode state |
| retail-data | UPC-A/EAN normalization, length boundaries and CV validation |
| retail-caption-edges | Caption clipping, origins, rotations and baseline placement |
| code93-controls | Full-ASCII shift controls and checksum captions |
| qr-module-state | QR magnification affecting subsequent barcode width |
| character-remap | Legacy CI remapping, persistence and barcode captions |
| box-minimum | Zero/omitted dimensions, thickness minimums and rounded boxes |
| field-block-rounding | Fractional justification spacing across fonts and gap counts |

Selection favors compact matrices and controls for distinct behaviors missing
from the older corpus. Five invalid UPC-E cases are explicitly classified as
invalid, and are never scored as successful blank renders. Other imported
cases are boundary probes: printer acceptance is not a claim of portable ZPL
validity. Duplicate corpus inputs and capture reset controls remain archived,
with exclusion reasons in `manifest.json`, but do not add execution weight.

The upstream inventory also contains larger resident-font, Unicode, QR Model 1,
MaxiCode, TLC39, text-layout and barcode sweeps. These were not imported in this
focused expansion. The `conformance` and `printer-accuracy` collections largely
mirror this repository; importing them wholesale would duplicate its weighting.
The older `font0-32` collection lacks the TSV provenance used for this import.

`test-data/render-conformance/generate.py` includes the selected exact input
bytes. Positive references are copied into the existing conformance reference
store and retain per-case source provenance. Its original batch timestamp and
repeat-control assertion do not describe these independent captures.

The corrected positive `databar_upce` capture comes from upstream
`zebra-http-api/tests/fixtures/barcodes-zd621-v1`, with eleven-digit payload
`04210000526`. The former six-digit request and blank printer response remain
in `databar-retail-zd621-v1/upce-original-invalid.*`. Historical Labelary records
for the replaced inputs are retained in `superseded-labelary`.
