# Real-printer barcode previews

Captured on 2026-09-15 from a ZTC ZD621-203dpi ZPL running V93.21.33Z.
`manifest.json` records the host, timestamp, exact request/image hashes, codyps/zpl
raster hashes and directional pixel differences. The `.png` files are the
printer's original HTTP preview responses, not locally generated references.
Each `.zpl` is the exact request that produced its accompanying PNG.

The fixed corpus covers all 29 barcode commands in 60 cases, including aliases,
DataBar variants, composites, MaxiCode modes, and CODABLOCK A (unsupported by codyps/zpl).
It is representative coverage, not every possible parameter or payload.

## Test contract

Run offline from the workspace root:

```sh
cargo test -p zebra-http-api --test barcode_preview
cargo run -p zebra-http-api --example barcode-compare -- \
  zebra-http-api/tests/fixtures/barcodes-zd621-v1 \
  --artifacts /tmp/barcode-review
```

The artifact directory must not exist. It receives codyps/zpl renders and directional
diff PNGs (magenta = printer only, cyan = codyps/zpl only). The command prints a
per-format Markdown report. No network access occurs without `--capture`.

The ordinary tests lock the **observed differences**, not a claim of parity.
They assert exact pixel hashes, dimensions, ink counts, difference counts and
diff hashes. Even an improvement fails until reviewed and deliberately recorded.
No percentage-of-white-background tolerance, registration, scaling or cropping
is applied. Unequal canvases are padded with white for the directional diff;
their dimension mismatch still prevents an exact match.

Initial results: **0 exact matches, 58 different renders, 1 blank printer preview
(`databar_upce`), 1 format unsupported by codyps/zpl (`codablock_a`)**. Printer canvases
are 832×1218, while codyps/zpl canvases are 812×1218 for the same `^PW812` request.
There are also nonzero ink differences, not just canvas-size differences.
The MaxiCode mode 5 preview appears to contain only the finder/orientation
features; nonblank output alone does not establish a valid encoded symbol.
These fixtures do not certify scanner readability or identify which side is
responsible for each mismatch. Independent decoder tests remain necessary.

The explicit strict gate currently fails, intentionally:

```sh
cargo test -p zebra-http-api --test barcode_preview \
  all_formats_match_printer_pixels -- --ignored
# Or add --strict to barcode-compare.
```

## New capture

Use a new directory to preserve the old evidence. Independently check and supply
the printer model/firmware before capture:

```sh
cargo run -p zebra-http-api --example barcode-compare -- \
  --capture --host http://PRINTER/ \
  --device 'MODEL; firmware VERSION' /tmp/barcode-new-capture
```

This performs 60 sequential preview submissions plus their image fetches, with
timeouts and same-origin redirects. It does not submit a physical print job.
A failed capture leaves its partial evidence in place and no final manifest.
Review new captures and renderer changes before updating the baseline; do not
automatically bless differences.
