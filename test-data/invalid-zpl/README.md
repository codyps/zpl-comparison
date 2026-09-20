# Invalid-ZPL corpus

[Run the suite](../../benchmarks/invalid/README.md) · [Measured results](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/invalid/README.md)

Run `python3 test-data/invalid-zpl/generate.py` to regenerate the 18 invalid/control pairs, or add `--check` to verify them without writes. The manifest records exact byte lengths, SHA-256 hashes, input rationale, reference commands and recovery caveats.

Malformed data, complete-label framing, and permissive fallback cases are separate groups. Every modified input has a valid control using the same feature. These fixtures are offline library tests and must not be included in printer capture runs.
