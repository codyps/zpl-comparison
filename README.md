# ZPL library comparison

Repeatable comparisons of ZPL parsers, generators and renderers, with performance, memory, deployment size and printer-reference accuracy measurements.

**[Latest CI-generated reports](https://github.com/codyps/zpl-comparison/tree/generated)**
are published automatically from `main` to an independent branch.

[![Rendering accuracy against printer references](docs/benchmarks/accuracy/accuracy.svg)](docs/benchmarks/accuracy/README.md)

- **[Compare library renders with printer previews](docs/benchmarks/accuracy/comparisons/README.md)**: browse by library or case; see the printer, render and difference together.
- [Compare feature fixtures](docs/benchmarks/accuracy/comparisons/features/README.md): all eight renderers, printer previews and differences.
- [Results, plots and tables](docs/benchmarks/README.md)
- [Which libraries reject invalid ZPL?](docs/benchmarks/invalid/README.md)
- [Browse support by library, command or feature](docs/compatibility/README.md)
- [Rendering conformance corpus](test-data/render-conformance/README.md)
- [Run the benchmarks](benchmarks/README.md)
- [Setup and provenance](PROVENANCE.md)

Support claims and measured rendering accuracy are separate evidence. Missing printer references are unscored, not passes.

Regenerate all derived resources from the collected data:

```sh
benchmarks/_work/venv/bin/python benchmarks/regenerate.py
```

This rebuilds the chart above, all other plots, reports, difference images, thumbnails and compatibility pages. See the [generation inventory and collection options](benchmarks/README.md#regenerate--test-the-harness).

## License

Licensed under the [Open Software License version 3.0](LICENSE).
