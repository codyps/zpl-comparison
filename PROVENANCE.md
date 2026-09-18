# Setup and provenance

The ZPL library is a separate dependency; its source is fetched into the ignored `benchmarks/_work/zpl` directory. Local setup uses your existing GitHub SSH access.

## Historical evidence

The checked-in performance, accuracy and conformance JSON files record historical runs. Their timestamps, host information and measurements identify those runs. Printer fixtures are stored in `references/barcodes-zd621-v1`.

The suite and harness are licensed under OSL-3.0 in LICENSE. The bundled Zebra Programming Guide retains Zebra's copyright and notices. Third-party library source is downloaded separately at revisions recorded in `benchmarks/sources.lock.json`; each library retains its own license.
