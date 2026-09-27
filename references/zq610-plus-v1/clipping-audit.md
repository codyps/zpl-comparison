# Native raster and clipping audit

All 116 paired case images were checked for ink bounds, native canvas size and
directional pixel errors. Wider ZD621 images expose clipped text even when the
last visible glyph does not touch the ZQ610 edge. Source field positions were
also reviewed: ink bounds alone cannot detect completely invisible objects.

Only three local-renderer discrepancies remain: rotated Font 0 B (1 missing,
3 extra pixels), I (5 missing, 3 extra), R (5 missing, 0 extra). Magnified
inspection shows isolated glyph-edge pixels, not missing text or shifted
fields. The same residuals occur on the ZD621. Foreground IoU is 98.54–99.26%.
All 60 barcode cases, shapes and unclipped replacements are pixel-exact locally.

| Clipped input | Visible comparison coverage |
| --- | --- |
| Original CODABLOCK A at x=60 | Campaign barcode at x=20, unchanged payload/modules; ink ends at x=381 |
| Inverted A/D/E text at x=300 | Existing `text-{A,D,E}-I-fit` moves to x=20, unchanged text/font |
| `canvas-width-120`, second box at x=360 | New `canvas-width-120-fit`, moves second box to x=80; native ink bounds x=12..99, 412 ink pixels |
| `canvas-width-300`, second box at x=360 | New `canvas-width-300-fit`, moves second box to x=260; bounds x=18..285, 412 ink pixels |
| `width-late-grow`, entirely invisible first box | New `width-late-grow-fit`, moves box to x=20; bounds x=24..43, 204 ink pixels |
| Oversized bars/markers in width boundary diagnostics | New `width-boundary-384-fit`, 340-dot bar and three complete fields inside x=20..359; 3460 ink pixels |

The four new companions have native captures on both printers and exact local
comparisons, with repeated controls and hashes in manifest.json. They are also
exported into the Rust regression corpus. Boundary diagnostics deliberately
retain clipping to exercise firmware width behavior; the visible companion
tests their drawing primitives without clipping. A blank diagnostic never
counts as positive rendering-accuracy evidence.

The all-library Bazel matrix includes these 116 inputs plus the four original
smoke cases, using unmodified sources and native printer references. Session
repeatability images remain acquisition evidence rather than duplicate cases.
