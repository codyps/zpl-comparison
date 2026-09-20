# External ZPL examples

Eight complete labels imported byte-for-byte from the pinned public repositories
in [manifest.json](manifest.json). They supplement the generated command probes
with independently authored layouts and command combinations.

[Browse the execution report and images](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/external-zpl/README.md).

| Source | Examples | License |
| --- | --- | --- |
| zpl-toolchain at `3da58518c1013fffd46d2147b0927a1d5b4aeab5` | Shipping, product, warehouse, compliance, UPS/USPS SurePost sample | [MIT](licenses/zpl-toolchain.txt) |
| ZPLr at `1c94eadfc5afb494b4c92dd10ad4808bd3d19529` | Asset Data Matrix/PDF417, retail UPC/EAN, stored resources | [MIT](licenses/zplr.txt) |

Each manifest entry links to its exact upstream file. These are library examples,
not carrier-certified labels or an independent holdout for their originating
libraries. The compliance example's name does not establish GS1 compliance.
No source bytes have been repaired, normalized or stripped of commands. All cases
are classified as boundary inputs because their semantics have not been certified.
Errors, blank output and unsupported commands remain observations in the report.

## Run and regenerate

After the adapter setup in [the benchmark guide](../../benchmarks/README.md):

```sh
benchmarks/_work/venv/bin/python benchmarks/conformance.py --corpus test-data/external-zpl --only all --output docs/benchmarks/external-zpl
benchmarks/_work/venv/bin/python -m unittest discover -s benchmarks -p 'test_*.py'
```

The command verifies fixture hashes, runs all 64 case/renderer combinations (including captured Labelary responses),
and regenerates JSON, PNGs and GitHub-rendered Markdown. CI runs the same command.
Use `--only codyps-zpl` for one renderer or `--group stateful` for stored resources.
Every case runs in a fresh process; all commands within that case remain together.
The existing adapters produce one output image per case. This suite does not test
persistence between separate processes or certify multi-page output.

Explicit `^PW`/`^LL` values determine the manifest dimensions when present.
The harness supplies 812×1218 dots for the compliance label, which omits both,
and 812×1524 for SurePost, which omits label length and has fields below dot 1400.
These are documented harness choices at 203 DPI, not inferred printer settings.
The 900-dot-wide asset example remains 900 dots wide; it is not resized to 832.

## Printer references and state

No printer captures are included, so every printer-accuracy score is N/A.
The SurePost sample includes media/configuration commands (`^MN`, `^MF`, `^MC`);
the stored-resource sample defines and recalls a format and a graphic
(`^DF`, `^XF`, `^FN`, `~DG`, `^XG`). Both are marked `capture_eligible: false`.
The capture tool additionally applies its rendering-command allowlist to the
remaining six examples. This import performs no printer operations.

The official Zebra exercises remain a specification reference in the bundled
[programming guide](../../docs/zpl-zbi2-pg-en.pdf); this directory imports the
redistributable repository fixtures rather than republishing manual excerpts.

To update an example, explicitly select an upstream commit, preserve its license,
replace the original file, and update its provenance and SHA-256 in the manifest.
Never silently rewrite an original to make a renderer pass; use a separately named
and documented derived case for adaptations.
