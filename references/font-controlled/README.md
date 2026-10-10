# Printer previews with supplied fonts

This is a separate baseline for `//:reports_fonts`. It does not replace the
resident-font captures used by `//:reports`.

The completed snapshot contains **1,077 previews**: 957 from the ZD621 and 120 from
the ZQ610 Plus. All accepted sessions passed repeated-font and restored-font
pixel controls. Both printers were restarted after capture to restore their
resident fonts.

The capture tool uploads the recovered native bitmap strikes with `~DB` and the
shared Heros TrueType bytes with binary `~DY`. Every preview selects the supplied
fonts through `^CW`, following the usual content-state reset and preceding the
unchanged fixture fields. Only HTTP **Preview Label** requests render labels;
there are no physical-print requests. GS and some internal barcode captions can
retain resident fonts.

- `capture.json`: device identities, timestamps, font/upload hashes, exact source
  and submission hashes, per-image hashes, session controls and recovery history.
- `submitted/`: the exact bytes submitted for each retained printer preview.
- `sessions/`: font installation evidence, repeat controls and restoration checks.
  Discarded sessions and failed preflights are retained for audit; their images
  never supply a comparison baseline.
- `overlay/`: new printer PNGs and matching reference manifests at the original
  logical paths, selected only for the controlled report.
- `catalog.json`: the verified manifest overlay used during Bazel analysis.
  An incomplete marker prevents building a partially refreshed controlled report.

ZQ610 captures use bounded sessions because long preview runs can stall its HTTP
service. Serial-verified restarts restore service and clear downloaded RAM fonts.
Every accepted session compares the resident control before and after restart.
This snapshot uses corrected Heros cap-height and x-height metadata, matching the
fonts supplied to the renderers. Earlier snapshots and preflight evidence remain
in Git history.

Reproduction and offline verification are documented in
[the font policy](../../benchmarks/fonts/README.md). Building reports and running
verification never contacts a printer. Live capture and restart flags must be
invoked explicitly.

The October 10, 2026 UTC refresh uses the corrected bitmap baseline bundle
`41b98e991bfa95ab221185199d9e8c84123cb4b42d0368664049e99af2ca08c4`.
All 1,077 previews were reacquired: 957 ZD621 and 120 ZQ610 Plus, with eight
accepted sessions and no discarded sessions. Every session passed repeated-font
and post-restart restoration controls. The previous snapshot remains in Git
history. Inputs and their native canvas dimensions remain unchanged.

The exporter now uses sourced baseline coordinates rather than inferring them
from sampled glyph bounds. See the baseline audit in
[the font policy](../../benchmarks/fonts/README.md). The fresh A/B/D–H normal
text controls and the reported LOGMARS/Code 128 examples match the resident-font
printer references exactly; that is not a claim that arbitrary downloaded-font
sizes or other renderers have pixel parity.
