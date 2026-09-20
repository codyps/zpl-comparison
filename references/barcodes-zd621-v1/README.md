# Real-printer barcode previews

Recaptured at 832 dots wide on 2026-09-18 UTC from the ZD621 identified in
manifest.json. All 60 original captures have been replaced. Each ZPL file is the
exact request; PNGs are original Preview Label responses. No physical printing
was requested. The manifest records hashes and the separate state-reset request
used before every case. Rendering comparisons live in docs/benchmarks/accuracy.

The previous 812-dot inputs caused this printer to center content on an 832-dot
preview canvas. These fixtures use ^PW832 so that width adjustment is outside the
accuracy benchmark. No alignment, cropping or rescaling is performed.
