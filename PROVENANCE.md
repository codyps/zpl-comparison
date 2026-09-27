# Setup and provenance

The ZPL library is a separate dependency; its source is fetched into the ignored `benchmarks/_work/zpl` directory. Local setup uses your existing GitHub SSH access.

## Historical evidence

The checked-in performance, accuracy and conformance JSON files record historical runs. Their timestamps, host information and measurements identify those runs. Printer fixtures are stored in `references/barcodes-zd621-v1`.

Third-party library source is downloaded separately at revisions recorded in `benchmarks/sources.lock.json`.

Additional printer controls and the corrected UPC-E capture were imported from
`codyps/zpl` at `de0676ae4a4b8728ed0ab75a18b112bae7cbe883`. See
[selection, source manifests and capture limitations](references/upstream-zd621/README.md).
