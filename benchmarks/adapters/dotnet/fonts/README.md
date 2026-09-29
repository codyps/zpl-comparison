# Pinned BinaryKits runtime fonts

These unmodified font assets and their licenses are copied from
[BinaryKits.Zpl 9d316458](https://github.com/BinaryKits/BinaryKits.Zpl/tree/9d316458c33c90608859cc935d3ba1e0c7587be7/src/BinaryKits.Zpl.Viewer.WebApi).
The upstream WebApi registers these same proportional and monospace faces.
The comparison adapter uses the public `FontManager.FontLoader` callback to
select them explicitly: font 0 uses TeX Gyre Heros Cn Bold; other text fonts
use DejaVu Sans Mono. This removes dependence on host fonts and avoids the
empty Skia typeface that crashed HarfBuzz on the Linux runner. These are
substitute viewer fonts, not extracted Zebra printer fonts.

The font files and licenses are copied into the relocatable adapter artifact,
and their hashes are included in `identity.json`. No third-party library
implementation is modified.
