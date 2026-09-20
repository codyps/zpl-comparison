# Invalid-ZPL rejection tests

**[Read the rejection and recovery report](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/invalid/README.md).**

The deterministic [fixture generator](../../test-data/invalid-zpl/generate.py) creates 18 modified inputs and 18 valid controls. Every pair runs through the supported default parser and renderer APIs of codyps/zpl, zpl-toolchain, labelize, zpl-forge, go-zpl, zpl-rs, BinaryKits.Zpl, and ZPLr. Builders that do not consume ZPL are N/A.

## Reproduce

Install the toolchains listed in the [benchmark setup](../README.md), including the .NET 8 runtime, then run from the repository root:

```sh
python3 -m venv benchmarks/_work/venv
benchmarks/_work/venv/bin/pip install -r benchmarks/requirements.txt
benchmarks/_work/venv/bin/python benchmarks/prepare.py
python3 test-data/invalid-zpl/generate.py --check
benchmarks/_work/venv/bin/python -m unittest discover -s benchmarks -p 'test_*.py'
benchmarks/_work/venv/bin/python benchmarks/invalid.py
benchmarks/_work/venv/bin/python benchmarks/invalid.py --check
```

The default run performs 1,008 executions: 18 pairs × 14 API lanes × two inputs × two repetitions. Each execution uses a fresh process and a ten-second timeout. The fixtures have a 400×300 canvas and small payloads. No printer or remote rendering service is contacted. Package/source pins are shared with the other benchmarks. Results retain fixture hashes, adapter identities, source/lockfile hashes, host information, raw verdicts, diagnostics and image hashes.

To preserve another machine's results or select a library:

```sh
benchmarks/_work/venv/bin/python benchmarks/invalid.py \
  --only codyps-zpl --repeats 2 --timeout 10 \
  --output benchmarks/_work/my-invalid-run
benchmarks/_work/venv/bin/python benchmarks/invalid.py \
  --output benchmarks/_work/my-invalid-run --check
```

`--report-only` regenerates Markdown from saved measurements. It does not execute adapters. `--check` verifies fixture hashes, matrix completeness, repetition counts, classifications and report freshness.

## Reading outcomes

- **Rejected:** the library returned an error, threw an exception, or returned an error-severity diagnostic; the matching control succeeded in all repeats. Partial ASTs may still accompany diagnostics.
- **Accepted:** no explicit error was reported. Warnings and recovery may still occur; this does not imply correct rendering.
- **Control failed:** the valid control errored, was empty, or rendered no ink. Rejection of the modified input cannot demonstrate supported validation.
- **Execution failure:** a panic, signal, timeout, unsuccessful process, missing output, or protocol problem occurred. These never count as successful rejection.
- **Unstable:** outcomes or rendered output changed across repetitions.

Malformed graphic encodings and nonnumeric EAN data have a separate summary from framing and fallback probes. The framing group requires complete labels; streaming parsers may intentionally accept fragments. Out-of-range parameters and malformed field escapes may be ignored, clamped, defaulted, or retained literally by permissive implementations. The fallback group is observational, not a standards pass/fail score. The [bundled Zebra guide](../../docs/zpl-zbi2-pg-en.pdf) documents command ranges, counted graphic payloads and recovery behavior; individual fixtures record their rationale.

The codyps/zpl parse lane exercises its byte framer. The zpl-toolchain lane uses heuristic `parse_str`, including returned diagnostics, without specification tables or the separate validator. Error acceptance in these lanes is not a claim about a library's optional validation APIs. Renderer probes use public analysis/rendering APIs and inspect explicit diagnostics where provided. Probe modes perform one operation, without benchmark warm-up or adapter assertions about label counts.

CI runs the entire suite and uploads the report, raw results and fixtures even if a probe crashes. Rejection-rate differences, failed controls and library crashes remain report data. Harness/process failures or instability fail the job after preserving results. Add `--fail-on-crash` to also return failure for library crashes or timeouts.
