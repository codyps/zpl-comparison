# ZPL library comparison

Repeatable comparisons of ZPL parsers, generators and renderers, with performance, memory, deployment size and printer-reference accuracy measurements.

**[Latest CI-generated reports](https://github.com/codyps/zpl-comparison/tree/generated)**
are published automatically from `main` to an independent branch.

[Font-free layout comparisons](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/accuracy/comparisons/layout/README.md)
cover 20 graphics and caption-free barcode probes against ZD621 previews.

[![Rendering accuracy against printer references](/../generated/docs/benchmarks/accuracy/accuracy.svg)](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/accuracy/README.md)

- **[Compare library renders with printer previews](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/accuracy/comparisons/README.md)**: browse by library or case; see the printer, render and difference together.
- [Compare feature fixtures](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/accuracy/comparisons/features/README.md): all eight renderers, printer previews and differences.
- [Results, plots and tables](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/README.md)
- [Which libraries reject invalid ZPL?](https://github.com/codyps/zpl-comparison/blob/generated/docs/benchmarks/invalid/README.md)
- [Browse support by library, command or feature](https://github.com/codyps/zpl-comparison/blob/generated/docs/compatibility/README.md)
- [Rendering conformance corpus](test-data/render-conformance/README.md)
- [Run the benchmarks](benchmarks/README.md)
- [Setup and provenance](PROVENANCE.md)

Support claims and measured rendering accuracy are separate evidence. Missing printer references are unscored, not passes.

Build pinned libraries, render locally, and assemble the reports in Bazel's output tree:

```sh
bazelisk build //:reports
```

Library builds, individual renders, comparisons, thumbnails, and report stages are cached independently. See [Bazel setup and cache behavior](benchmarks/README.md#regenerate--test-the-harness).

Source branches retain maintained documentation, fixture manifests/cases, and saved
measurement and capture inputs required by Bazel. Derived reports, plots,
differences, thumbnails, and galleries are ignored here and published only on
[`generated`](https://github.com/codyps/zpl-comparison/tree/generated).
For an offline rebuild from saved renderer images, use `bazelisk build //:reports_saved`.

## License

Licensed under the [Open Software License version 3.0](LICENSE).
