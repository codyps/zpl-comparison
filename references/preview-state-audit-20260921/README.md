# ZD621 preview-state audit, 2026-09-21

The external `zpl-toolchain-shipping_label` preview is accurate for its unchanged
source on ZTC ZD621-203dpi ZPL, firmware V93.21.33Z. Recapturing it reproduces the
original pixels. The investigation did find two capture-procedure defects:
barcode height was initialized to 100 instead of 10, and legacy character
remappings survived the reset. Both are fixed in
[`capture.py`](../../benchmarks/accuracy/capture.py).

All observations are HTTP **Preview Label**, not physical print/scan. No firmware
reset, calibration, persistent configuration save, or Print request was used.
The before-state is main commit `749cb2e81ff842f1d5ac0f5fc067795ee5eec8ce`.
Source bytes were preserved; each submitted prefix and request hash is recorded.

## Shipping label

The [diagnostic controls](legacy-controls/manifest.json) establish:

- Original, repeated, units-reset, and post-layout-contamination submissions
  produce identical pixels. The six capturable external examples also reproduce
  under the old reset (`external-legacy-reset.json`).
- Changing only `^PW812` to `^PW832` removes exactly ten dots of horizontal
  displacement. The complete image otherwise matches after that diagnostic
  translation. The 812-dot source is centered in this firmware's 832-dot preview.
- The source's `^BY3,2,100` precedes both barcodes. Its QR at `^FO600,50` starts at
  y=149: this ZD621 applies `^BY` height minus one to the QR field origin.
  A diagnostic `^BY3,2,1` immediately before the QR moves its top to y=50.

Those changes are diagnostic variants, not replacements for the external source.
The adopted shipping PNG remains byte-identical. The poor renderer comparison
score therefore cannot be attributed to stale printer state. Production scores
remain at the original origin, without alignment or resizing.

## Capture fixes

1. Use `^BY2,3,10`, matching Zebra's documented power-up barcode height.
   The former reset used 100. Eleven conformance `probe-qr-*` inputs omit a `^BY`
   height, so their old references inherited the harness's value. Their corrected
   images move exactly 90 dots upward. Independent reverse-order recaptures match
   all eleven corrected PNGs (`qr-reverse-repeat.json`). Explicit `^BY` values in
   source still take precedence, including the shipping label's height 100.
2. Restore all 256 source/destination pairs in the legacy CI0 and CI13 mapping
   tables before selecting CI27. `^CI27` alone does not clear these tables.
   `encoding-remap` leaves B mapped to A; subsequent barcode captions can use
   that legacy table even while ordinary text selects CI27. The intermediate
   height-only run exposed nine conformance, two argument, and one warehouse-label
   caption changes. None of those contaminated images was adopted. The final
   reset restores their original pixels. The targeted `remap-controls` sequence
   verifies correct captions immediately after the remapping case and checks
   both CI0 and CI13 text. Fixture-local intentional remapping remains intact.

`preview_reset()` generates the complete prefix and every final manifest records
it verbatim. The reset is inline with each fixture, before its source commands.
This is a controlled rendering baseline, not a factory reset. Other legacy
encodings, device models, firmware versions, and concurrent clients are outside
this audit's proof.

Authoritative command definitions: [Zebra ^BY](https://docs.zebra.com/us/en/printers/software/zpl-pg/zpl-commands/%5Eby.html)
and [Zebra ^CI](https://docs.zebra.com/us/en/printers/software/zpl-pg/c-zpl-zpl-commands/r-zpl-ci.html).
The latter allows up to 256 source/destination pairs; equal pairs restore the
corresponding character designations. The persistent-table and caption effects
above are measured device behavior, also documented in the imported
[character-remapping controls](../upstream-zd621/character-remap-zd621-v1/README.md).

## Final coverage

| Active reference set | Cases excluding repeat control | Changed images |
|---|---:|---:|
| Conformance | 573 | 11 QR probes |
| Argument accuracy | 73 | 0 |
| Font-free layout | 20 | 0 |
| External examples | 6 | 0 |
| Archived barcode accuracy | 60 | 0 |
| Total | 732 | 11 |

Five repeated controls also passed. All existing active successful captures were
recaptured sequentially with the final reset. Six previously unavailable
conformance inputs remained unavailable: two empty formats, CI29/CI30 that had
stalled the printer, and two binary/NUL raster cases. They were not resubmitted.
Invalid/non-capturable corpus entries and unused historical archives were not
promoted to successful references.

The final `conformance.json`, `arguments.json`, `layout.json`, `external.json`, and
`barcodes.json` contain per-case source, old/new PNG and submitted-request hashes,
capture times, dimensions, pixel-equality results, and missing/failure inventories.
The conformance and external reference manifests were refreshed from the final
capture; unchanged argument/layout/barcode references retain their original
capture provenance, with fresh verification recorded here.

`height-only-*.json` records the intermediate experiment before character-map
cleanup. `height-only-captures` preserves its twelve contaminated images;
`legacy-defaults` preserves six 100-dot barcode observations from the interrupted
old-reset experiment. These are diagnostic evidence, not scored references.
`superseded-qr` preserves the eleven former reference PNGs.

## Verify and reproduce

```sh
benchmarks/_work/venv/bin/python references/preview-state-audit-20260921/verify_controls.py
benchmarks/_work/venv/bin/python -m unittest discover -s benchmarks -p 'test_*.py'
bazelisk build //:reports_saved
```

The offline control verifier checks archived hashes, exact shipping translations,
legacy-state observations, final reference hashes, and the independent QR repeat.
The capture/audit tests cover reset ordering, explicit source overrides, hash
corruption, unchanged-alpha RGB differences, canvas changes, missing captures,
and actual repeated-control pixels.

To repeat a live suite, use `capture.py --corpus test-data/render-conformance`
(or `test-data/external-zpl` / `test-data/layout-accuracy`), a new output directory,
and a dedicated RAM object name. Preserve the six known unavailable conformance
inputs with `--skip` and `--skip-reason`. The argument suite uses `capture.py`
without `--corpus`. Compare a completed new capture with the previous directory
using `audit_captures.py SAVED FRESH --output AUDIT.json`; differences deliberately
return a nonzero exit status for review. Do not resume across a reset change.
