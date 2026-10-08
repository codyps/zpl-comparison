# ZD621 ROM font comparisons

On 2026-10-08, the ZD621 `D7J211001302`, 203 dpi, firmware `V93.21.33Z`,
listed 78 `.FNT` / `.TTF` resources in `Z:`. The exact directory response is
preserved in `directory.html`; `inventory.json` records its hash, timestamp,
origin, and all font filenames. No `.TTE` resources were listed.

The `fonts-rom` conformance group selects every exact filename using `^A@`,
including fonts that have no single-character alias. Each label contains two
fields: default dimensions (`0,0`) and explicit dimensions (`32,24`). The
sample is `Ag09!?`, except `GS.FNT`, which uses symbols `ABCDE`. Existing
alphanumeric-selector and GS rotation comparisons remain in the corpus.

`capture/` contains 78 original ZPL inputs and printer HTTP Preview Label PNGs,
plus a repeated first-case control. Its manifest records firmware, timestamps,
source/image hashes, the reset and submitted-byte hashes. All requests succeeded
and the repeated control matched pixel-for-pixel. These are printer previews,
not physical print scans. Capture did not download fonts or assign aliases;
named requests avoid dependence on the device's mutable single-character aliases.

Three resources produced entirely blank previews: `Z:EPL6.FNT`, `Z:EPL7.FNT`,
and `Z:LMU.FNT`. Their exact responses remain available, but the corpus marks
them as diagnostic references with no fidelity score. The other 75 are scored.
A listed resource need not be a distinct face, and successful rendering does not
prove that a requested font was used without fallback. Coverage is of these
requests and samples, not every glyph or encoding each font may support.

All 79 identical source labels were submitted to Labelary. Every response was
HTTP 200, decoded as an 832×1218 PNG, and is preserved under
`docs/benchmarks/labelary/images/conformance--font-rom-*.png` and
`conformance--font-installed-tt0003m_-ttf.png`, with request
provenance in `docs/benchmarks/labelary/captures.json`.

The printer references are adopted in
`benchmarks/accuracy/conformance-reference/` and linked to this independent
batch by `refresh_batches`. The older manifest's top-level capture timestamp and
repeat control describe its original batch, not this one. The capture's corpus
hash describes the inventory before the three observed blank cases were marked
unscored; their ZPL bytes did not change.

The all-device directory also listed one installed font, `E:TT0003M_.TTF`.
`directory-all.html` and its inventory hash preserve that observation. The
`fonts-installed` group covers it separately; `installed-capture/` contains its
preview and matching repeat control. Both the ZD621 and Labelary returned
nonblank images. Thus the added coverage is 79 named font paths in total.

The normal `//:reports` target includes these cases across the renderer matrix.
A focused example is:

```sh
bazel build //:reports --output_groups=case_conformance_font-rom-tt0003m_-ttf
```

Capture reproduction (use a new output directory to preserve this evidence):

```sh
python benchmarks/accuracy/capture.py \
  --host http://d7j211001302.bed.einic.org/ \
  --corpus test-data/render-conformance --group fonts-rom \
  --output references/zd621-fonts-new --object-name CMPFONTS
python benchmarks/labelary.py --extend
```

`benchmarks/test_conformance.py` verifies the ROM inventory, exact named requests,
capture eligibility, stable printer control, adopted reference hashes, matching
Labelary source/image hashes and dimensions, and the blank-reference exclusions.
