# ZQ610 Plus: every rendering candidate

120 native ZQ610 outputs (116 paired campaign cases and four original smoke
cases) are compared with all eight rendering candidates: codyps-zpl, labelize,
forge, go, ffi, binarykits, zplr and Labelary. Session repeatability captures
remain provenance rather than duplicate scored test cases.

The exact submitted ZPL is passed unchanged, with the native printer's width
and height as adapter options. codyps-zpl explicitly uses `ZQ610_PLUS_203_DPI`; other candidates use their
pinned library defaults. Dimensions alone do not select a device profile.
The codyps-zpl candidate is the revision in sources.lock.json; the separate
paired gallery measures the current checkout's ZQ610 profile. These identities
are intentionally explicit, so a pinned older renderer is not represented as
the current profile implementation.

Different output dimensions are unscored canvas mismatches. No padding,
cropping, resizing or alignment is used for metrics. Equal native canvases
use directional ink counts and foreground IoU. Blank diagnostics, execution
failures and uncaptured candidates remain visible and never become fabricated
positive matches. Candidate raster hashes are checked before comparison.

Aztec observations here include the printer-state reset prefix. zpl-forge
0.3.2 rejects its `^CI` remapping arguments before reaching the barcode;
these errors do not establish an Aztec limitation. The site links these cases
to the independent conformance `symbol-aztec`, `symbol-aztec_alias`, and
`symbol-aztec_rune` comparisons. Dedicated `encoding-remap-control` and
`encoding-remap-identity` fixtures separately compare `^CI0` with `^CI0,0,0`;
`encoding-remap` continues to check non-identity remapping. Captured sources
and their hashes remain unchanged.

The [canvas dimension audit](../../docs/canvas-dimension-audit.md) lists the
26 cases previously affected by the default ZD621 profile and the validation.

## Acquisition and offline generation

`manifest.json` indexes every native source and PNG hash and records the
paired/smoke provenance digests. `labelary/captures.json` records all 120
successful HTTP responses, request/response UTC timestamps, source hashes,
requested dimensions, response headers, image hashes and decoded dimensions.
The PNGs under `labelary/images` are unchanged API responses. Labelary exposes
no renderer version in these responses; timestamps identify the observations.

```sh
python benchmarks/zq610_candidates.py prepare
python benchmarks/zq610_candidates.py labelary
bazelisk build //:reports --output_groups=suite_zq610_candidates
python benchmarks/zq610_candidates.py save-candidates
bazelisk build //:reports_saved --output_groups=suite_zq610_candidates
```

The Labelary command is an explicit network acquisition step. Bazel never
contacts the rendering API. The live report target has independent render and
comparison actions per case/library; the saved target imports recorded images
and observations without compiling or executing any candidate. Both full
report assemblies include the gallery at `docs/benchmarks/zq610-candidates`.
`saved/results.json` preserves execution timestamps and adapter artifact hashes.

On a Nix host without `/bin/bash` or conventional shared-library paths, pass
the host shell with `--shell_executable`, expose PATH to both configurations
with `--action_env=PATH --host_action_env=PATH`, and provide the installed ICU,
OpenSSL, zlib, C++ runtime, fontconfig and freetype library directories through
`LD_LIBRARY_PATH` and the corresponding action/host-action environment flags.
This supplies runtime dependencies without changing captured sources or pixels.
