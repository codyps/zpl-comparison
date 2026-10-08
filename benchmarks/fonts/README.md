# Font-controlled comparisons

`bazel build //:reports_fonts` produces a separate version of every rendering
comparison in `bazel-bin/reports_fonts`. The existing `//:reports` keeps its
original fonts. Fixtures, saved printer references, scoring and renderer
versions are the same. No printer or service requests are made.

```sh
bazel build //:reports //:reports_fonts
bazel run //:comparison_site -- \
  --input "$PWD/bazel-bin/reports" \
  --font-input "$PWD/bazel-bin/reports_fonts" \
  --output "$PWD/benchmarks/_work/site-with-fonts"
```

Trusted CI builds both variants and publishes the controlled comparison under
`fonts/`, with links between the sites. Fork previews retain the default saved
comparison: historical observations cannot be relabeled as font-controlled.
Performance and invalid-input probes retain their original fonts; this variant
controls rendering accuracy comparisons, not their measurement protocols.

## Shared assets

The recovered ZBF strikes in `recovered/` come from `codyps/zpl` at the revision
and SHA-256 hashes in `sources.json`. They contain observed printer pixels and
advances, not commercial font files. We use the native A, B, D, E, F, G, H, GS
and P–V strikes; C aliases D. Available cent and corrected hyphen captures are
merged into those strikes. Other uncaptured characters retain the receiving
library's missing-glyph behavior. These are ZD621 captures, also used explicitly
as the common supplied assets in the ZQ610 comparison; they do not establish
that both printers have identical fonts.

`build.py` packages the recovered glyphs in two ways:

- Native `~DB` bitmap downloads, including bearings and advances, for ZPLr.
- TrueType glyphs made of horizontal pixel-run rectangles, for outline-only
  APIs. Every edge and advance uses an integral multiple of 16 font units.
  No smoothing, tracing, fitting, kerning or optical adjustment is applied.

Font 0 uses a TrueType conversion of **TeX Gyre Heros Condensed Bold**, a
Helvetica-family condensed bold substitute for Zebra's CG Triumvirate Bold
Condensed. Named `TT0003M_` / Swiss requests use **TeX Gyre Heros Regular**.
These are shape-based choices, not claims of metric equivalence or an optimized
fit to the scored corpus. The [TeX Gyre project description](https://www.gust.org.pl/projects/e-foundry/tex-gyre/heros)
describes Heros's Nimbus Sans / Helvetica lineage. Zebra's bundled Programming
Guide documents its resident font families and dimensions.

The original Heros OpenType/CFF sources and GUST license are retained under
`source/`. Condensed Bold is the already pinned BinaryKits font asset; Regular
comes from CTAN at the URL recorded in `sources.json`. The conversion uses the
repository's pinned FontTools, quadratic curves with at most one font-unit
approximation error, original advances and renamed `ComparisonHeros*` families.
It does not preserve CFF hinting or layout tables. The font bundle and its
manifest are generated deterministically; no host font installation is used.

## Renderer treatment

| Renderer | Font supply and limits |
| --- | --- |
| BinaryKits | Public `FontManager.FontLoader`; recovered outline carriers and Heros substitutions. Includes captions that call that callback. Unknown IDs retain the adapter's pinned fallback. |
| zpl-forge | Public `FontManager.register_font` and `ZplEngine.set_fonts`; 0, A–H, P–V. GS and unsupported/named IDs retain defaults. |
| ZPLr | Native `~DB` and `^CW` for recovered bitmap IDs; `FontProvider` and `^CW` for font 0. Named Swiss uses the same provider. GS and internally generated captions can retain built-ins. |
| Zebrash, zpl-renderer-js, zebrash-ts | Public ZPL `~DU` TrueType downloads and `^CW` aliases. No patching of library internals. GS and internally generated barcode captions can retain built-ins. |
| codyps/zpl | Fixed embedded recovered strikes; the comparison API has no external font provider. |
| labelize | Fixed embedded faces; no renderer font-loader API. |
| go-zpl, Rust FFI wrapper | Fixed internal font manager, with no public replacement API. |
| Labelary | Original captured response with service fonts; explicitly fixed, not a new font-supplied capture. |

Supplying fonts reduces one source of difference; **it does not eliminate font
rendering differences**. Libraries retain their baseline placement, width
normalization, hinting, rasterization, antialiasing, missing-glyph and spacing
behavior. Downloaded fonts can follow scalable-font sizing instead of resident
bitmap quantization. The Zebrash parser's `^CF` alias resolution and library
reset/delete/alias commands also remain library behavior. Fixture commands can
replace supplied aliases; we do not rewrite field commands to override them.

Download-based adapters receive a font-resource preamble followed by the exact
original fixture bytes. The original `source_sha256` still identifies the
scored fixture; `submitted_source_sha256` identifies the prefixed bytes.
Callbacks apply only where supported. Every row includes `font_control` with
supply mode, limitations, font mapping and bundle hash, including fixed-font
rows. Missing/corrupt font assets fail the build rather than silently falling
back. Render actions declare the bundle as an input, keeping controlled and
default cache entries separate. Font-controlled saved replay is deliberately
unsupported until an archive with matching font identities is available.

## Verification

`bazel test //:font_profile_test` checks every recovered pixel rectangle and
advance against its ZBF input, deterministic bundle generation, fixed-font
policy, actual text changes in all six configurable renderers, and unchanged
non-text graphics. Use ordinary report output groups on `//:reports_fonts` to
build a suite or individual case, for example:

```sh
bazel build //:reports_fonts --output_groups=case_accuracy_argument-font-A
```
