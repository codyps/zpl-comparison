# Paired ZD621 Labelary responses

These are exact Labelary responses for all 116 ZD621 inputs from
`references/zq610-plus-v1`. Their original native canvases are requested at
8 dots/mm. Source hashes, HTTP responses, timestamps and PNG hashes are retained
in `captures.json`; errors are observations, never replaced with synthetic images.

The matching ZQ610 responses already exist under
`references/zq610-candidates/labelary` and are reused by source hash and canvas.

Verify offline with `python benchmarks/paired_labelary.py`. Explicitly capture
missing public inputs with `python benchmarks/paired_labelary.py --capture`.
The 116 submitted files were verified byte-identical to the public repository at
commit `b9e25a2f2ed930c29c0efa4f92b81b5c894e54c2` before submission.
