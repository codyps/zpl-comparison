# Invalid ZPL: rejection and recovery

[Reproduce this run](../../../benchmarks/invalid/README.md) · [Exact fixtures](../../../test-data/invalid-zpl/manifest.json) · [Raw results and diagnostics](results.json)

Measured **2026-09-18T23:45:19Z** on `macOS-26.6.2-x86_64-i386-64bit-Mach-O`. 18 paired cases, 14 API lanes, 2 repetitions per input: **1008 executions**.

Each modified input is paired with a valid control using the same feature. **Rejected** means a returned library error, thrown exception, or error-severity diagnostic, with a successful control in every repeat. **Accepted** means no explicit error was reported; warnings may still appear. **Control failed** is inconclusive, including blank renderer controls. Panics, signals, timeouts, process/protocol failures and unstable outcomes never count as proper rejection.

Parser lanes use the same default APIs as the benchmarks: codyps/zpl frames bytes; zpl-toolchain uses heuristic `parse_str` without specification tables or its separate validator. Renderer lanes run analysis and rendering. Error diagnostics may accompany a partial AST. These tests measure error signaling, not atomic refusal to produce any output or full standards validation. Builders (zpl-builder, Python ZPL, JSZPL) are N/A because they do not consume ZPL.

The malformed group tests corrupt data; framing tests impose a complete-label contract that streaming APIs need not enforce. Fallback probes use invalid/out-of-range arguments for which ignoring, clamping or defaulting may be intentional. They are reported separately and do not contribute to malformed-data rejection counts. No case is sent to a printer.

## Malformed-data results

| Library | API | Rejected | Accepted | Control failed | Execution failure | Unstable |
| --- | --- | --- | --- | --- | --- | --- |
| codyps/zpl (Rust) | parse | 2 | 5 | 0 | 0 | 0 |
| codyps/zpl (Rust) | render | 7 | 0 | 0 | 0 | 0 |
| zpl-toolchain (Rust) | parse | 0 | 6 | 1 | 0 | 0 |
| labelize (Rust) | parse | 2 | 3 | 2 | 0 | 0 |
| labelize (Rust) | render | 3 | 2 | 2 | 0 | 0 |
| zpl-forge (Rust) | parse | 0 | 6 | 1 | 0 | 0 |
| zpl-forge (Rust) | render | 1 | 5 | 1 | 0 | 0 |
| go-zpl (Go) | parse | 0 | 7 | 0 | 0 | 0 |
| go-zpl (Go) | render | 0 | 7 | 0 | 0 | 0 |
| zpl-rs (Rust → Go) | render | 0 | 7 | 0 | 0 | 0 |
| BinaryKits.Zpl (.NET) | parse | 3 | 3 | 1 | 0 | 0 |
| BinaryKits.Zpl (.NET) | render | 4 | 2 | 1 | 0 | 0 |
| ZPLr (TypeScript) | parse | 1 | 6 | 0 | 0 | 0 |
| ZPLr (TypeScript) | render | 0 | 6 | 1 | 0 | 0 |


## Malformed cases

| Case | Library | API | Outcome |
| --- | --- | --- | --- |
| [raster-invalid-hex](#raster-invalid-hex) | codyps/zpl (Rust) | parse | accepted |
| [raster-invalid-hex](#raster-invalid-hex) | codyps/zpl (Rust) | render | rejected |
| [raster-invalid-hex](#raster-invalid-hex) | zpl-toolchain (Rust) | parse | accepted |
| [raster-invalid-hex](#raster-invalid-hex) | labelize (Rust) | parse | rejected |
| [raster-invalid-hex](#raster-invalid-hex) | labelize (Rust) | render | rejected |
| [raster-invalid-hex](#raster-invalid-hex) | zpl-forge (Rust) | parse | accepted |
| [raster-invalid-hex](#raster-invalid-hex) | zpl-forge (Rust) | render | accepted |
| [raster-invalid-hex](#raster-invalid-hex) | go-zpl (Go) | parse | accepted |
| [raster-invalid-hex](#raster-invalid-hex) | go-zpl (Go) | render | accepted |
| [raster-invalid-hex](#raster-invalid-hex) | zpl-rs (Rust → Go) | render | accepted |
| [raster-invalid-hex](#raster-invalid-hex) | BinaryKits.Zpl (.NET) | parse | rejected |
| [raster-invalid-hex](#raster-invalid-hex) | BinaryKits.Zpl (.NET) | render | rejected |
| [raster-invalid-hex](#raster-invalid-hex) | ZPLr (TypeScript) | parse | accepted |
| [raster-invalid-hex](#raster-invalid-hex) | ZPLr (TypeScript) | render | accepted |
| [raster-short-data](#raster-short-data) | codyps/zpl (Rust) | parse | accepted |
| [raster-short-data](#raster-short-data) | codyps/zpl (Rust) | render | rejected |
| [raster-short-data](#raster-short-data) | zpl-toolchain (Rust) | parse | accepted |
| [raster-short-data](#raster-short-data) | labelize (Rust) | parse | accepted |
| [raster-short-data](#raster-short-data) | labelize (Rust) | render | accepted |
| [raster-short-data](#raster-short-data) | zpl-forge (Rust) | parse | accepted |
| [raster-short-data](#raster-short-data) | zpl-forge (Rust) | render | accepted |
| [raster-short-data](#raster-short-data) | go-zpl (Go) | parse | accepted |
| [raster-short-data](#raster-short-data) | go-zpl (Go) | render | accepted |
| [raster-short-data](#raster-short-data) | zpl-rs (Rust → Go) | render | accepted |
| [raster-short-data](#raster-short-data) | BinaryKits.Zpl (.NET) | parse | accepted |
| [raster-short-data](#raster-short-data) | BinaryKits.Zpl (.NET) | render | accepted |
| [raster-short-data](#raster-short-data) | ZPLr (TypeScript) | parse | accepted |
| [raster-short-data](#raster-short-data) | ZPLr (TypeScript) | render | accepted |
| [binary-truncated](#binary-truncated) | codyps/zpl (Rust) | parse | rejected |
| [binary-truncated](#binary-truncated) | codyps/zpl (Rust) | render | rejected |
| [binary-truncated](#binary-truncated) | zpl-toolchain (Rust) | parse | control failed |
| [binary-truncated](#binary-truncated) | labelize (Rust) | parse | accepted |
| [binary-truncated](#binary-truncated) | labelize (Rust) | render | accepted |
| [binary-truncated](#binary-truncated) | zpl-forge (Rust) | parse | control failed |
| [binary-truncated](#binary-truncated) | zpl-forge (Rust) | render | control failed |
| [binary-truncated](#binary-truncated) | go-zpl (Go) | parse | accepted |
| [binary-truncated](#binary-truncated) | go-zpl (Go) | render | accepted |
| [binary-truncated](#binary-truncated) | zpl-rs (Rust → Go) | render | accepted |
| [binary-truncated](#binary-truncated) | BinaryKits.Zpl (.NET) | parse | control failed |
| [binary-truncated](#binary-truncated) | BinaryKits.Zpl (.NET) | render | control failed |
| [binary-truncated](#binary-truncated) | ZPLr (TypeScript) | parse | rejected |
| [binary-truncated](#binary-truncated) | ZPLr (TypeScript) | render | control failed |
| [base64-alphabet](#base64-alphabet) | codyps/zpl (Rust) | parse | rejected |
| [base64-alphabet](#base64-alphabet) | codyps/zpl (Rust) | render | rejected |
| [base64-alphabet](#base64-alphabet) | zpl-toolchain (Rust) | parse | accepted |
| [base64-alphabet](#base64-alphabet) | labelize (Rust) | parse | control failed |
| [base64-alphabet](#base64-alphabet) | labelize (Rust) | render | control failed |
| [base64-alphabet](#base64-alphabet) | zpl-forge (Rust) | parse | accepted |
| [base64-alphabet](#base64-alphabet) | zpl-forge (Rust) | render | accepted |
| [base64-alphabet](#base64-alphabet) | go-zpl (Go) | parse | accepted |
| [base64-alphabet](#base64-alphabet) | go-zpl (Go) | render | accepted |
| [base64-alphabet](#base64-alphabet) | zpl-rs (Rust → Go) | render | accepted |
| [base64-alphabet](#base64-alphabet) | BinaryKits.Zpl (.NET) | parse | rejected |
| [base64-alphabet](#base64-alphabet) | BinaryKits.Zpl (.NET) | render | rejected |
| [base64-alphabet](#base64-alphabet) | ZPLr (TypeScript) | parse | accepted |
| [base64-alphabet](#base64-alphabet) | ZPLr (TypeScript) | render | accepted |
| [base64-crc](#base64-crc) | codyps/zpl (Rust) | parse | accepted |
| [base64-crc](#base64-crc) | codyps/zpl (Rust) | render | rejected |
| [base64-crc](#base64-crc) | zpl-toolchain (Rust) | parse | accepted |
| [base64-crc](#base64-crc) | labelize (Rust) | parse | control failed |
| [base64-crc](#base64-crc) | labelize (Rust) | render | control failed |
| [base64-crc](#base64-crc) | zpl-forge (Rust) | parse | accepted |
| [base64-crc](#base64-crc) | zpl-forge (Rust) | render | accepted |
| [base64-crc](#base64-crc) | go-zpl (Go) | parse | accepted |
| [base64-crc](#base64-crc) | go-zpl (Go) | render | accepted |
| [base64-crc](#base64-crc) | zpl-rs (Rust → Go) | render | accepted |
| [base64-crc](#base64-crc) | BinaryKits.Zpl (.NET) | parse | accepted |
| [base64-crc](#base64-crc) | BinaryKits.Zpl (.NET) | render | accepted |
| [base64-crc](#base64-crc) | ZPLr (TypeScript) | parse | accepted |
| [base64-crc](#base64-crc) | ZPLr (TypeScript) | render | accepted |
| [z64-invalid-stream](#z64-invalid-stream) | codyps/zpl (Rust) | parse | accepted |
| [z64-invalid-stream](#z64-invalid-stream) | codyps/zpl (Rust) | render | rejected |
| [z64-invalid-stream](#z64-invalid-stream) | zpl-toolchain (Rust) | parse | accepted |
| [z64-invalid-stream](#z64-invalid-stream) | labelize (Rust) | parse | rejected |
| [z64-invalid-stream](#z64-invalid-stream) | labelize (Rust) | render | rejected |
| [z64-invalid-stream](#z64-invalid-stream) | zpl-forge (Rust) | parse | accepted |
| [z64-invalid-stream](#z64-invalid-stream) | zpl-forge (Rust) | render | accepted |
| [z64-invalid-stream](#z64-invalid-stream) | go-zpl (Go) | parse | accepted |
| [z64-invalid-stream](#z64-invalid-stream) | go-zpl (Go) | render | accepted |
| [z64-invalid-stream](#z64-invalid-stream) | zpl-rs (Rust → Go) | render | accepted |
| [z64-invalid-stream](#z64-invalid-stream) | BinaryKits.Zpl (.NET) | parse | rejected |
| [z64-invalid-stream](#z64-invalid-stream) | BinaryKits.Zpl (.NET) | render | rejected |
| [z64-invalid-stream](#z64-invalid-stream) | ZPLr (TypeScript) | parse | accepted |
| [z64-invalid-stream](#z64-invalid-stream) | ZPLr (TypeScript) | render | accepted |
| [ean-nonnumeric](#ean-nonnumeric) | codyps/zpl (Rust) | parse | accepted |
| [ean-nonnumeric](#ean-nonnumeric) | codyps/zpl (Rust) | render | rejected |
| [ean-nonnumeric](#ean-nonnumeric) | zpl-toolchain (Rust) | parse | accepted |
| [ean-nonnumeric](#ean-nonnumeric) | labelize (Rust) | parse | accepted |
| [ean-nonnumeric](#ean-nonnumeric) | labelize (Rust) | render | rejected |
| [ean-nonnumeric](#ean-nonnumeric) | zpl-forge (Rust) | parse | accepted |
| [ean-nonnumeric](#ean-nonnumeric) | zpl-forge (Rust) | render | rejected |
| [ean-nonnumeric](#ean-nonnumeric) | go-zpl (Go) | parse | accepted |
| [ean-nonnumeric](#ean-nonnumeric) | go-zpl (Go) | render | accepted |
| [ean-nonnumeric](#ean-nonnumeric) | zpl-rs (Rust → Go) | render | accepted |
| [ean-nonnumeric](#ean-nonnumeric) | BinaryKits.Zpl (.NET) | parse | accepted |
| [ean-nonnumeric](#ean-nonnumeric) | BinaryKits.Zpl (.NET) | render | rejected |
| [ean-nonnumeric](#ean-nonnumeric) | ZPLr (TypeScript) | parse | accepted |
| [ean-nonnumeric](#ean-nonnumeric) | ZPLr (TypeScript) | render | accepted |


## Framing cases

| Case | Library | API | Outcome |
| --- | --- | --- | --- |
| [missing-end](#missing-end) | codyps/zpl (Rust) | parse | accepted |
| [missing-end](#missing-end) | codyps/zpl (Rust) | render | rejected |
| [missing-end](#missing-end) | zpl-toolchain (Rust) | parse | rejected |
| [missing-end](#missing-end) | labelize (Rust) | parse | accepted |
| [missing-end](#missing-end) | labelize (Rust) | render | accepted |
| [missing-end](#missing-end) | zpl-forge (Rust) | parse | accepted |
| [missing-end](#missing-end) | zpl-forge (Rust) | render | accepted |
| [missing-end](#missing-end) | go-zpl (Go) | parse | accepted |
| [missing-end](#missing-end) | go-zpl (Go) | render | accepted |
| [missing-end](#missing-end) | zpl-rs (Rust → Go) | render | accepted |
| [missing-end](#missing-end) | BinaryKits.Zpl (.NET) | parse | accepted |
| [missing-end](#missing-end) | BinaryKits.Zpl (.NET) | render | accepted |
| [missing-end](#missing-end) | ZPLr (TypeScript) | parse | rejected |
| [missing-end](#missing-end) | ZPLr (TypeScript) | render | accepted |
| [truncated-command](#truncated-command) | codyps/zpl (Rust) | parse | rejected |
| [truncated-command](#truncated-command) | codyps/zpl (Rust) | render | rejected |
| [truncated-command](#truncated-command) | zpl-toolchain (Rust) | parse | rejected |
| [truncated-command](#truncated-command) | labelize (Rust) | parse | accepted |
| [truncated-command](#truncated-command) | labelize (Rust) | render | accepted |
| [truncated-command](#truncated-command) | zpl-forge (Rust) | parse | rejected |
| [truncated-command](#truncated-command) | zpl-forge (Rust) | render | rejected |
| [truncated-command](#truncated-command) | go-zpl (Go) | parse | accepted |
| [truncated-command](#truncated-command) | go-zpl (Go) | render | accepted |
| [truncated-command](#truncated-command) | zpl-rs (Rust → Go) | render | accepted |
| [truncated-command](#truncated-command) | BinaryKits.Zpl (.NET) | parse | accepted |
| [truncated-command](#truncated-command) | BinaryKits.Zpl (.NET) | render | accepted |
| [truncated-command](#truncated-command) | ZPLr (TypeScript) | parse | rejected |
| [truncated-command](#truncated-command) | ZPLr (TypeScript) | render | accepted |


## Fallback cases

| Case | Library | API | Outcome |
| --- | --- | --- | --- |
| [orientation](#orientation) | codyps/zpl (Rust) | parse | accepted |
| [orientation](#orientation) | codyps/zpl (Rust) | render | rejected |
| [orientation](#orientation) | zpl-toolchain (Rust) | parse | accepted |
| [orientation](#orientation) | labelize (Rust) | parse | accepted |
| [orientation](#orientation) | labelize (Rust) | render | accepted |
| [orientation](#orientation) | zpl-forge (Rust) | parse | accepted |
| [orientation](#orientation) | zpl-forge (Rust) | render | accepted |
| [orientation](#orientation) | go-zpl (Go) | parse | accepted |
| [orientation](#orientation) | go-zpl (Go) | render | accepted |
| [orientation](#orientation) | zpl-rs (Rust → Go) | render | accepted |
| [orientation](#orientation) | BinaryKits.Zpl (.NET) | parse | accepted |
| [orientation](#orientation) | BinaryKits.Zpl (.NET) | render | accepted |
| [orientation](#orientation) | ZPLr (TypeScript) | parse | accepted |
| [orientation](#orientation) | ZPLr (TypeScript) | render | accepted |
| [negative-width](#negative-width) | codyps/zpl (Rust) | parse | accepted |
| [negative-width](#negative-width) | codyps/zpl (Rust) | render | rejected |
| [negative-width](#negative-width) | zpl-toolchain (Rust) | parse | accepted |
| [negative-width](#negative-width) | labelize (Rust) | parse | accepted |
| [negative-width](#negative-width) | labelize (Rust) | render | accepted |
| [negative-width](#negative-width) | zpl-forge (Rust) | parse | rejected |
| [negative-width](#negative-width) | zpl-forge (Rust) | render | rejected |
| [negative-width](#negative-width) | go-zpl (Go) | parse | accepted |
| [negative-width](#negative-width) | go-zpl (Go) | render | accepted |
| [negative-width](#negative-width) | zpl-rs (Rust → Go) | render | accepted |
| [negative-width](#negative-width) | BinaryKits.Zpl (.NET) | parse | accepted |
| [negative-width](#negative-width) | BinaryKits.Zpl (.NET) | render | accepted |
| [negative-width](#negative-width) | ZPLr (TypeScript) | parse | accepted |
| [negative-width](#negative-width) | ZPLr (TypeScript) | render | accepted |
| [alignment](#alignment) | codyps/zpl (Rust) | parse | accepted |
| [alignment](#alignment) | codyps/zpl (Rust) | render | rejected |
| [alignment](#alignment) | zpl-toolchain (Rust) | parse | accepted |
| [alignment](#alignment) | labelize (Rust) | parse | accepted |
| [alignment](#alignment) | labelize (Rust) | render | accepted |
| [alignment](#alignment) | zpl-forge (Rust) | parse | accepted |
| [alignment](#alignment) | zpl-forge (Rust) | render | accepted |
| [alignment](#alignment) | go-zpl (Go) | parse | accepted |
| [alignment](#alignment) | go-zpl (Go) | render | accepted |
| [alignment](#alignment) | zpl-rs (Rust → Go) | render | accepted |
| [alignment](#alignment) | BinaryKits.Zpl (.NET) | parse | accepted |
| [alignment](#alignment) | BinaryKits.Zpl (.NET) | render | accepted |
| [alignment](#alignment) | ZPLr (TypeScript) | parse | accepted |
| [alignment](#alignment) | ZPLr (TypeScript) | render | accepted |
| [field-hex](#field-hex) | codyps/zpl (Rust) | parse | accepted |
| [field-hex](#field-hex) | codyps/zpl (Rust) | render | rejected |
| [field-hex](#field-hex) | zpl-toolchain (Rust) | parse | accepted |
| [field-hex](#field-hex) | labelize (Rust) | parse | accepted |
| [field-hex](#field-hex) | labelize (Rust) | render | accepted |
| [field-hex](#field-hex) | zpl-forge (Rust) | parse | accepted |
| [field-hex](#field-hex) | zpl-forge (Rust) | render | accepted |
| [field-hex](#field-hex) | go-zpl (Go) | parse | accepted |
| [field-hex](#field-hex) | go-zpl (Go) | render | accepted |
| [field-hex](#field-hex) | zpl-rs (Rust → Go) | render | accepted |
| [field-hex](#field-hex) | BinaryKits.Zpl (.NET) | parse | accepted |
| [field-hex](#field-hex) | BinaryKits.Zpl (.NET) | render | accepted |
| [field-hex](#field-hex) | ZPLr (TypeScript) | parse | accepted |
| [field-hex](#field-hex) | ZPLr (TypeScript) | render | accepted |
| [field-hex-truncated](#field-hex-truncated) | codyps/zpl (Rust) | parse | accepted |
| [field-hex-truncated](#field-hex-truncated) | codyps/zpl (Rust) | render | rejected |
| [field-hex-truncated](#field-hex-truncated) | zpl-toolchain (Rust) | parse | accepted |
| [field-hex-truncated](#field-hex-truncated) | labelize (Rust) | parse | accepted |
| [field-hex-truncated](#field-hex-truncated) | labelize (Rust) | render | accepted |
| [field-hex-truncated](#field-hex-truncated) | zpl-forge (Rust) | parse | accepted |
| [field-hex-truncated](#field-hex-truncated) | zpl-forge (Rust) | render | accepted |
| [field-hex-truncated](#field-hex-truncated) | go-zpl (Go) | parse | accepted |
| [field-hex-truncated](#field-hex-truncated) | go-zpl (Go) | render | accepted |
| [field-hex-truncated](#field-hex-truncated) | zpl-rs (Rust → Go) | render | accepted |
| [field-hex-truncated](#field-hex-truncated) | BinaryKits.Zpl (.NET) | parse | accepted |
| [field-hex-truncated](#field-hex-truncated) | BinaryKits.Zpl (.NET) | render | accepted |
| [field-hex-truncated](#field-hex-truncated) | ZPLr (TypeScript) | parse | accepted |
| [field-hex-truncated](#field-hex-truncated) | ZPLr (TypeScript) | render | accepted |
| [zero-stride](#zero-stride) | codyps/zpl (Rust) | parse | accepted |
| [zero-stride](#zero-stride) | codyps/zpl (Rust) | render | rejected |
| [zero-stride](#zero-stride) | zpl-toolchain (Rust) | parse | accepted |
| [zero-stride](#zero-stride) | labelize (Rust) | parse | accepted |
| [zero-stride](#zero-stride) | labelize (Rust) | render | accepted |
| [zero-stride](#zero-stride) | zpl-forge (Rust) | parse | accepted |
| [zero-stride](#zero-stride) | zpl-forge (Rust) | render | execution failure |
| [zero-stride](#zero-stride) | go-zpl (Go) | parse | accepted |
| [zero-stride](#zero-stride) | go-zpl (Go) | render | accepted |
| [zero-stride](#zero-stride) | zpl-rs (Rust → Go) | render | accepted |
| [zero-stride](#zero-stride) | BinaryKits.Zpl (.NET) | parse | rejected |
| [zero-stride](#zero-stride) | BinaryKits.Zpl (.NET) | render | rejected |
| [zero-stride](#zero-stride) | ZPLr (TypeScript) | parse | accepted |
| [zero-stride](#zero-stride) | ZPLr (TypeScript) | render | accepted |
| [qr-model](#qr-model) | codyps/zpl (Rust) | parse | accepted |
| [qr-model](#qr-model) | codyps/zpl (Rust) | render | rejected |
| [qr-model](#qr-model) | zpl-toolchain (Rust) | parse | accepted |
| [qr-model](#qr-model) | labelize (Rust) | parse | accepted |
| [qr-model](#qr-model) | labelize (Rust) | render | accepted |
| [qr-model](#qr-model) | zpl-forge (Rust) | parse | accepted |
| [qr-model](#qr-model) | zpl-forge (Rust) | render | accepted |
| [qr-model](#qr-model) | go-zpl (Go) | parse | accepted |
| [qr-model](#qr-model) | go-zpl (Go) | render | accepted |
| [qr-model](#qr-model) | zpl-rs (Rust → Go) | render | accepted |
| [qr-model](#qr-model) | BinaryKits.Zpl (.NET) | parse | accepted |
| [qr-model](#qr-model) | BinaryKits.Zpl (.NET) | render | accepted |
| [qr-model](#qr-model) | ZPLr (TypeScript) | parse | accepted |
| [qr-model](#qr-model) | ZPLr (TypeScript) | render | accepted |
| [qr-mask](#qr-mask) | codyps/zpl (Rust) | parse | accepted |
| [qr-mask](#qr-mask) | codyps/zpl (Rust) | render | rejected |
| [qr-mask](#qr-mask) | zpl-toolchain (Rust) | parse | accepted |
| [qr-mask](#qr-mask) | labelize (Rust) | parse | accepted |
| [qr-mask](#qr-mask) | labelize (Rust) | render | accepted |
| [qr-mask](#qr-mask) | zpl-forge (Rust) | parse | accepted |
| [qr-mask](#qr-mask) | zpl-forge (Rust) | render | accepted |
| [qr-mask](#qr-mask) | go-zpl (Go) | parse | accepted |
| [qr-mask](#qr-mask) | go-zpl (Go) | render | accepted |
| [qr-mask](#qr-mask) | zpl-rs (Rust → Go) | render | accepted |
| [qr-mask](#qr-mask) | BinaryKits.Zpl (.NET) | parse | accepted |
| [qr-mask](#qr-mask) | BinaryKits.Zpl (.NET) | render | accepted |
| [qr-mask](#qr-mask) | ZPLr (TypeScript) | parse | accepted |
| [qr-mask](#qr-mask) | ZPLr (TypeScript) | render | accepted |
| [encoding](#encoding) | codyps/zpl (Rust) | parse | accepted |
| [encoding](#encoding) | codyps/zpl (Rust) | render | rejected |
| [encoding](#encoding) | zpl-toolchain (Rust) | parse | accepted |
| [encoding](#encoding) | labelize (Rust) | parse | accepted |
| [encoding](#encoding) | labelize (Rust) | render | accepted |
| [encoding](#encoding) | zpl-forge (Rust) | parse | accepted |
| [encoding](#encoding) | zpl-forge (Rust) | render | accepted |
| [encoding](#encoding) | go-zpl (Go) | parse | accepted |
| [encoding](#encoding) | go-zpl (Go) | render | accepted |
| [encoding](#encoding) | zpl-rs (Rust → Go) | render | accepted |
| [encoding](#encoding) | BinaryKits.Zpl (.NET) | parse | accepted |
| [encoding](#encoding) | BinaryKits.Zpl (.NET) | render | accepted |
| [encoding](#encoding) | ZPLr (TypeScript) | parse | accepted |
| [encoding](#encoding) | ZPLr (TypeScript) | render | accepted |


## Inputs and diagnostics

### missing-end

One complete ^XA...^XZ label is required by this suite. Single-label input contract; streaming framers can intentionally accept fragments.

Reference: ^XA/^XZ. [Valid control](../../../test-data/invalid-zpl/cases/missing-end-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/missing-end-invalid.zpl)

**codyps/zpl (Rust) / parse: accepted**

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 42, message: "unterminated label (missing XZ)" }
invalid, repeat 2, rejected: RenderError { offset: 42, message: "unterminated label (missing XZ)" }
~~~

**zpl-toolchain (Rust) / parse: rejected**

~~~text
invalid, repeat 1, rejected: Diagnostic { id: "ZPL.PARSER.1102", severity: Error, message: "missing terminator (^XZ)", span: Some(Span { start: 42, end: 42 }), context: Some({"expected": "^XZ", "suggested_edit.kind": "insert", "suggested_edit.position": "document.end", "suggested_edit.text": "^XZ", "suggested_edit.title": "Insert ^XZ (label terminator)"}) }
Parser returned error diagnostics
invalid, repeat 2, rejected: Diagnostic { id: "ZPL.PARSER.1102", severity: Error, message: "missing terminator (^XZ)", span: Some(Span { start: 42, end: 42 }), context: Some({"expected": "^XZ", "suggested_edit.kind": "insert", "suggested_edit.position": "document.end", "suggested_edit.text": "^XZ", "suggested_edit.title": "Insert ^XZ (label terminator)"}) }
Parser returned error diagnostics
~~~

**labelize (Rust) / parse: accepted**

**labelize (Rust) / render: accepted**

**zpl-forge (Rust) / parse: accepted**

**zpl-forge (Rust) / render: accepted**

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: accepted**

**BinaryKits.Zpl (.NET) / render: accepted**

**ZPLr (TypeScript) / parse: rejected**

~~~text
invalid, repeat 1, rejected: {"code":"UNTERMINATED_FORMAT","message":"The label started with XA but did not end with XZ.","span":{"start":0,"end":42},"severity":"error","phase":"parse","labelIndex":0}
invalid, repeat 2, rejected: {"code":"UNTERMINATED_FORMAT","message":"The label started with XA but did not end with XZ.","span":{"start":0,"end":42},"severity":"error","phase":"parse","labelIndex":0}
~~~

**ZPLr (TypeScript) / render: accepted**

### truncated-command

A command prefix is missing its two-character command code. A streaming framer may wait for more bytes.

Reference: ZPL command framing. [Valid control](../../../test-data/invalid-zpl/cases/truncated-command-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/truncated-command-invalid.zpl)

**codyps/zpl (Rust) / parse: rejected**

~~~text
invalid, repeat 1, rejected: ParseError { offset: 42, kind: IncompleteCommand }
invalid, repeat 2, rejected: ParseError { offset: 42, kind: IncompleteCommand }
~~~

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 42, message: "ZPL framing error at byte 42: IncompleteCommand" }
invalid, repeat 2, rejected: RenderError { offset: 42, message: "ZPL framing error at byte 42: IncompleteCommand" }
~~~

**zpl-toolchain (Rust) / parse: rejected**

~~~text
invalid, repeat 1, rejected: Diagnostic { id: "ZPL.PARSER.1001", severity: Error, message: "invalid command: expected command code after leader", span: Some(Span { start: 42, end: 43 }), context: Some({"command": "^"}) }
Diagnostic { id: "ZPL.PARSER.1102", severity: Error, message: "missing terminator (^XZ)", span: Some(Span { start: 43, end: 43 }), context: Some({"expected": "^XZ", "suggested_edit.kind": "insert", "suggested_edit.position": "document.end", "suggested_edit.text": "^XZ", "suggested_edit.title": "Insert ^XZ (label terminator)"}) }
Parser returned error diagnostics
invalid, repeat 2, rejected: Diagnostic { id: "ZPL.PARSER.1001", severity: Error, message: "invalid command: expected command code after leader", span: Some(Span { start: 42, end: 43 }), context: Some({"command": "^"}) }
Diagnostic { id: "ZPL.PARSER.1102", severity: Error, message: "missing terminator (^XZ)", span: Some(Span { start: 43, end: 43 }), context: Some({"expected": "^XZ", "suggested_edit.kind": "insert", "suggested_edit.position": "document.end", "suggested_edit.text": "^XZ", "suggested_edit.title": "Insert ^XZ (label terminator)"}) }
Parser returned error diagnostics
~~~

**labelize (Rust) / parse: accepted**

**labelize (Rust) / render: accepted**

**zpl-forge (Rust) / parse: rejected**

~~~text
invalid, repeat 1, rejected: ParseError { line: 1, message: "Invalid or malformed ZPL command (Error code: Eof)" }
invalid, repeat 2, rejected: ParseError { line: 1, message: "Invalid or malformed ZPL command (Error code: Eof)" }
~~~

**zpl-forge (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: ParseError { line: 1, message: "Invalid or malformed ZPL command (Error code: Eof)" }
invalid, repeat 2, rejected: ParseError { line: 1, message: "Invalid or malformed ZPL command (Error code: Eof)" }
~~~

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: accepted**

**BinaryKits.Zpl (.NET) / render: accepted**

**ZPLr (TypeScript) / parse: rejected**

~~~text
invalid, repeat 1, rejected: {"code":"INVALID_COMMAND","message":"A command prefix was not followed by a valid ZPL command code.","span":{"start":42,"end":43},"severity":"error","phase":"parse"}
{"code":"UNTERMINATED_FORMAT","message":"The label started with XA but did not end with XZ.","span":{"start":0,"end":42},"severity":"error","phase":"parse","labelIndex":0}
invalid, repeat 2, rejected: {"code":"INVALID_COMMAND","message":"A command prefix was not followed by a valid ZPL command code.","span":{"start":42,"end":43},"severity":"error","phase":"parse"}
{"code":"UNTERMINATED_FORMAT","message":"The label started with XA but did not end with XZ.","span":{"start":0,"end":42},"severity":"error","phase":"parse","labelIndex":0}
~~~

**ZPLr (TypeScript) / render: accepted**

### raster-invalid-hex

Question marks are not hexadecimal digits or graphic RLE tokens. Malformed graphic data.

Reference: ^GF, guide p. 215. [Valid control](../../../test-data/invalid-zpl/cases/raster-invalid-hex-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/raster-invalid-hex-invalid.zpl)

**codyps/zpl (Rust) / parse: accepted**

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 23, message: "invalid graphic hex digit" }
invalid, repeat 2, rejected: RenderError { offset: 23, message: "invalid graphic hex digit" }
~~~

**zpl-toolchain (Rust) / parse: accepted**

**labelize (Rust) / parse: rejected**

~~~text
invalid, repeat 1, rejected: "failed to decode hex string: hex decode error: invalid hex char: ?"
invalid, repeat 2, rejected: "failed to decode hex string: hex decode error: invalid hex char: ?"
~~~

**labelize (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: "failed to decode hex string: hex decode error: invalid hex char: ?"
invalid, repeat 2, rejected: "failed to decode hex string: hex decode error: invalid hex char: ?"
~~~

**zpl-forge (Rust) / parse: accepted**

**zpl-forge (Rust) / render: accepted**

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: rejected**

~~~text
invalid, repeat 1, rejected: Cannot analyze command ^GFA,8,8,1,??818181818181FF System.FormatException: The input is not a valid hex string as it contains a non-hex character.
   at System.Convert.FromHexString(ReadOnlySpan`1 chars)
   at System.Convert.FromHexString(String s)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.HexToBytes(String hex)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.ToBytesFromHex(String hex)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
invalid, repeat 2, rejected: Cannot analyze command ^GFA,8,8,1,??818181818181FF System.FormatException: The input is not a valid hex string as it contains a non-hex character.
   at System.Convert.FromHexString(ReadOnlySpan`1 chars)
   at System.Convert.FromHexString(String s)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.HexToBytes(String hex)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.ToBytesFromHex(String hex)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
~~~

**BinaryKits.Zpl (.NET) / render: rejected**

~~~text
invalid, repeat 1, rejected: Cannot analyze command ^GFA,8,8,1,??818181818181FF System.FormatException: The input is not a valid hex string as it contains a non-hex character.
   at System.Convert.FromHexString(ReadOnlySpan`1 chars)
   at System.Convert.FromHexString(String s)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.HexToBytes(String hex)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.ToBytesFromHex(String hex)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
invalid, repeat 2, rejected: Cannot analyze command ^GFA,8,8,1,??818181818181FF System.FormatException: The input is not a valid hex string as it contains a non-hex character.
   at System.Convert.FromHexString(ReadOnlySpan`1 chars)
   at System.Convert.FromHexString(String s)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.HexToBytes(String hex)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.ToBytesFromHex(String hex)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
~~~

**ZPLr (TypeScript) / parse: accepted**

~~~text
control, repeat 1, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":50},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
control, repeat 2, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":50},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
invalid, repeat 1, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":50},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
invalid, repeat 2, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":50},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
~~~

**ZPLr (TypeScript) / render: accepted**

### raster-short-data

Eight graphic bytes are declared but only two are supplied. A command prefix may abort a download; acceptance can mean recovery, not complete decoding.

Reference: ^GF, guide p. 215. [Valid control](../../../test-data/invalid-zpl/cases/raster-short-data-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/raster-short-data-invalid.zpl)

**codyps/zpl (Rust) / parse: accepted**

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 23, message: "graphic byte count mismatch" }
invalid, repeat 2, rejected: RenderError { offset: 23, message: "graphic byte count mismatch" }
~~~

**zpl-toolchain (Rust) / parse: accepted**

**labelize (Rust) / parse: accepted**

**labelize (Rust) / render: accepted**

**zpl-forge (Rust) / parse: accepted**

**zpl-forge (Rust) / render: accepted**

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: accepted**

**BinaryKits.Zpl (.NET) / render: accepted**

**ZPLr (TypeScript) / parse: accepted**

~~~text
control, repeat 1, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":50},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
control, repeat 2, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":50},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
invalid, repeat 1, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":38},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
invalid, repeat 2, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":38},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
~~~

**ZPLr (TypeScript) / render: accepted**

### binary-truncated

Eight binary bytes are declared but the stream ends after one. EOF occurs inside counted data; no printer is contacted.

Reference: ^GF, guide p. 215. [Valid control](../../../test-data/invalid-zpl/cases/binary-truncated-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/binary-truncated-invalid.zpl)

**codyps/zpl (Rust) / parse: rejected**

~~~text
invalid, repeat 1, rejected: ParseError { offset: 23, kind: TruncatedBinaryData }
invalid, repeat 2, rejected: ParseError { offset: 23, kind: TruncatedBinaryData }
~~~

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 23, message: "ZPL framing error at byte 23: TruncatedBinaryData" }
invalid, repeat 2, rejected: RenderError { offset: 23, message: "ZPL framing error at byte 23: TruncatedBinaryData" }
~~~

**zpl-toolchain (Rust) / parse: control failed**

~~~text
control, repeat 1, rejected: invalid utf-8 sequence of 1 bytes from index 34
control, repeat 2, rejected: invalid utf-8 sequence of 1 bytes from index 34
invalid, repeat 1, rejected: invalid utf-8 sequence of 1 bytes from index 34
invalid, repeat 2, rejected: invalid utf-8 sequence of 1 bytes from index 34
~~~

**labelize (Rust) / parse: accepted**

**labelize (Rust) / render: accepted**

**zpl-forge (Rust) / parse: control failed**

~~~text
control, repeat 1, rejected: invalid utf-8 sequence of 1 bytes from index 34
control, repeat 2, rejected: invalid utf-8 sequence of 1 bytes from index 34
invalid, repeat 1, rejected: invalid utf-8 sequence of 1 bytes from index 34
invalid, repeat 2, rejected: invalid utf-8 sequence of 1 bytes from index 34
~~~

**zpl-forge (Rust) / render: control failed**

~~~text
control, repeat 1, rejected: invalid utf-8 sequence of 1 bytes from index 34
control, repeat 2, rejected: invalid utf-8 sequence of 1 bytes from index 34
invalid, repeat 1, rejected: invalid utf-8 sequence of 1 bytes from index 34
invalid, repeat 2, rejected: invalid utf-8 sequence of 1 bytes from index 34
~~~

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: control failed**

~~~text
control, repeat 1, rejected: Cannot analyze command ^GFB,8,8,1,�������� System.FormatException: The input is not a valid hex string as it contains a non-hex character.
   at System.Convert.FromHexString(ReadOnlySpan`1 chars)
   at System.Convert.FromHexString(String s)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.HexToBytes(String hex)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.ToBytesFromHex(String hex)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
control, repeat 2, rejected: Cannot analyze command ^GFB,8,8,1,�������� System.FormatException: The input is not a valid hex string as it contains a non-hex character.
   at System.Convert.FromHexString(ReadOnlySpan`1 chars)
   at System.Convert.FromHexString(String s)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.HexToBytes(String hex)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.ToBytesFromHex(String hex)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
invalid, repeat 1, rejected: Cannot analyze command ^GFB,8,8,1,� System.FormatException: The input is not a valid hex string as its length is not a multiple of 2.
   at System.Convert.FromHexString(ReadOnlySpan`1 chars)
   at System.Convert.FromHexString(String s)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.HexToBytes(String hex)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.ToBytesFromHex(String hex)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
invalid, repeat 2, rejected: Cannot analyze command ^GFB,8,8,1,� System.FormatException: The input is not a valid hex string as its length is not a multiple of 2.
   at System.Convert.FromHexString(ReadOnlySpan`1 chars)
   at System.Convert.FromHexString(String s)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.HexToBytes(String hex)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.ToBytesFromHex(String hex)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
~~~

**BinaryKits.Zpl (.NET) / render: control failed**

~~~text
control, repeat 1, rejected: Cannot analyze command ^GFB,8,8,1,�������� System.FormatException: The input is not a valid hex string as it contains a non-hex character.
   at System.Convert.FromHexString(ReadOnlySpan`1 chars)
   at System.Convert.FromHexString(String s)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.HexToBytes(String hex)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.ToBytesFromHex(String hex)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
control, repeat 2, rejected: Cannot analyze command ^GFB,8,8,1,�������� System.FormatException: The input is not a valid hex string as it contains a non-hex character.
   at System.Convert.FromHexString(ReadOnlySpan`1 chars)
   at System.Convert.FromHexString(String s)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.HexToBytes(String hex)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.ToBytesFromHex(String hex)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
invalid, repeat 1, rejected: Cannot analyze command ^GFB,8,8,1,� System.FormatException: The input is not a valid hex string as its length is not a multiple of 2.
   at System.Convert.FromHexString(ReadOnlySpan`1 chars)
   at System.Convert.FromHexString(String s)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.HexToBytes(String hex)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.ToBytesFromHex(String hex)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
invalid, repeat 2, rejected: Cannot analyze command ^GFB,8,8,1,� System.FormatException: The input is not a valid hex string as its length is not a multiple of 2.
   at System.Convert.FromHexString(ReadOnlySpan`1 chars)
   at System.Convert.FromHexString(String s)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.HexToBytes(String hex)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.ToBytesFromHex(String hex)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
~~~

**ZPLr (TypeScript) / parse: rejected**

~~~text
control, repeat 1, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":42},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
control, repeat 2, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":42},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
invalid, repeat 1, rejected: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":35},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
{"code":"UNTERMINATED_FORMAT","message":"The label started with XA but did not end with XZ.","span":{"start":0,"end":35},"severity":"error","phase":"parse","labelIndex":0}
invalid, repeat 2, rejected: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":35},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
{"code":"UNTERMINATED_FORMAT","message":"The label started with XA but did not end with XZ.","span":{"start":0,"end":35},"severity":"error","phase":"parse","labelIndex":0}
~~~

**ZPLr (TypeScript) / render: control failed**

### base64-alphabet

Exclamation marks are outside the Base64 alphabet. Tests encoded graphic decoding.

Reference: Zebra alternate data encoding. [Valid control](../../../test-data/invalid-zpl/cases/base64-alphabet-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/base64-alphabet-invalid.zpl)

**codyps/zpl (Rust) / parse: rejected**

~~~text
invalid, repeat 1, rejected: ParseError { offset: 23, kind: InvalidEncodedData }
invalid, repeat 2, rejected: ParseError { offset: 23, kind: InvalidEncodedData }
~~~

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 23, message: "ZPL framing error at byte 23: InvalidEncodedData" }
invalid, repeat 2, rejected: RenderError { offset: 23, message: "ZPL framing error at byte 23: InvalidEncodedData" }
~~~

**zpl-toolchain (Rust) / parse: accepted**

**labelize (Rust) / parse: control failed**

~~~text
control, repeat 1, rejected: "failed to decode hex string: hex decode error: invalid hex char: /"
control, repeat 2, rejected: "failed to decode hex string: hex decode error: invalid hex char: /"
~~~

**labelize (Rust) / render: control failed**

~~~text
control, repeat 1, rejected: "failed to decode hex string: hex decode error: invalid hex char: /"
control, repeat 2, rejected: "failed to decode hex string: hex decode error: invalid hex char: /"
~~~

**zpl-forge (Rust) / parse: accepted**

**zpl-forge (Rust) / render: accepted**

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: rejected**

~~~text
invalid, repeat 1, rejected: Cannot analyze command ^GFA,8,8,1,:B64:!!!!:0000 System.FormatException: The input is not a valid Base-64 string as it contains a non-base 64 character, more than two padding characters, or an illegal character among the padding characters.
   at System.Convert.FromBase64CharPtr(Char* inputPtr, Int32 inputLength)
   at System.Convert.FromBase64String(String s)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.FromBase64(String base64)
   at BinaryKits.Zpl.Label.Helpers.ZebraB64CompressionHelper.Uncompress(String hexData)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
invalid, repeat 2, rejected: Cannot analyze command ^GFA,8,8,1,:B64:!!!!:0000 System.FormatException: The input is not a valid Base-64 string as it contains a non-base 64 character, more than two padding characters, or an illegal character among the padding characters.
   at System.Convert.FromBase64CharPtr(Char* inputPtr, Int32 inputLength)
   at System.Convert.FromBase64String(String s)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.FromBase64(String base64)
   at BinaryKits.Zpl.Label.Helpers.ZebraB64CompressionHelper.Uncompress(String hexData)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
~~~

**BinaryKits.Zpl (.NET) / render: rejected**

~~~text
invalid, repeat 1, rejected: Cannot analyze command ^GFA,8,8,1,:B64:!!!!:0000 System.FormatException: The input is not a valid Base-64 string as it contains a non-base 64 character, more than two padding characters, or an illegal character among the padding characters.
   at System.Convert.FromBase64CharPtr(Char* inputPtr, Int32 inputLength)
   at System.Convert.FromBase64String(String s)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.FromBase64(String base64)
   at BinaryKits.Zpl.Label.Helpers.ZebraB64CompressionHelper.Uncompress(String hexData)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
invalid, repeat 2, rejected: Cannot analyze command ^GFA,8,8,1,:B64:!!!!:0000 System.FormatException: The input is not a valid Base-64 string as it contains a non-base 64 character, more than two padding characters, or an illegal character among the padding characters.
   at System.Convert.FromBase64CharPtr(Char* inputPtr, Int32 inputLength)
   at System.Convert.FromBase64String(String s)
   at BinaryKits.Zpl.Label.Helpers.ByteHelper.FromBase64(String base64)
   at BinaryKits.Zpl.Label.Helpers.ZebraB64CompressionHelper.Uncompress(String hexData)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
~~~

**ZPLr (TypeScript) / parse: accepted**

~~~text
control, repeat 1, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":56},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
control, repeat 2, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":56},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
invalid, repeat 1, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":48},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
invalid, repeat 2, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":48},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
~~~

**ZPLr (TypeScript) / render: accepted**

### base64-crc

The supplied checksum differs from CRC-16 of the encoded payload. Control uses the correct checksum.

Reference: Zebra alternate data encoding. [Valid control](../../../test-data/invalid-zpl/cases/base64-crc-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/base64-crc-invalid.zpl)

**codyps/zpl (Rust) / parse: accepted**

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 23, message: "graphic CRC mismatch" }
invalid, repeat 2, rejected: RenderError { offset: 23, message: "graphic CRC mismatch" }
~~~

**zpl-toolchain (Rust) / parse: accepted**

**labelize (Rust) / parse: control failed**

~~~text
control, repeat 1, rejected: "failed to decode hex string: hex decode error: invalid hex char: /"
control, repeat 2, rejected: "failed to decode hex string: hex decode error: invalid hex char: /"
invalid, repeat 1, rejected: "failed to decode hex string: hex decode error: invalid hex char: /"
invalid, repeat 2, rejected: "failed to decode hex string: hex decode error: invalid hex char: /"
~~~

**labelize (Rust) / render: control failed**

~~~text
control, repeat 1, rejected: "failed to decode hex string: hex decode error: invalid hex char: /"
control, repeat 2, rejected: "failed to decode hex string: hex decode error: invalid hex char: /"
invalid, repeat 1, rejected: "failed to decode hex string: hex decode error: invalid hex char: /"
invalid, repeat 2, rejected: "failed to decode hex string: hex decode error: invalid hex char: /"
~~~

**zpl-forge (Rust) / parse: accepted**

**zpl-forge (Rust) / render: accepted**

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: accepted**

**BinaryKits.Zpl (.NET) / render: accepted**

**ZPLr (TypeScript) / parse: accepted**

~~~text
control, repeat 1, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":56},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
control, repeat 2, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":56},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
invalid, repeat 1, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":56},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
invalid, repeat 2, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":56},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
~~~

**ZPLr (TypeScript) / render: accepted**

### z64-invalid-stream

Valid Base64 and CRC wrap bytes that are not a zlib stream. Control uses zlib-compressed graphic bytes.

Reference: Zebra alternate data encoding. [Valid control](../../../test-data/invalid-zpl/cases/z64-invalid-stream-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/z64-invalid-stream-invalid.zpl)

**codyps/zpl (Rust) / parse: accepted**

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 23, message: "invalid zlib header" }
invalid, repeat 2, rejected: RenderError { offset: 23, message: "invalid zlib header" }
~~~

**zpl-toolchain (Rust) / parse: accepted**

**labelize (Rust) / parse: rejected**

~~~text
invalid, repeat 1, rejected: "failed to decode hex string: zlib decompress error: corrupt deflate stream"
invalid, repeat 2, rejected: "failed to decode hex string: zlib decompress error: corrupt deflate stream"
~~~

**labelize (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: "failed to decode hex string: zlib decompress error: corrupt deflate stream"
invalid, repeat 2, rejected: "failed to decode hex string: zlib decompress error: corrupt deflate stream"
~~~

**zpl-forge (Rust) / parse: accepted**

**zpl-forge (Rust) / render: accepted**

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: rejected**

~~~text
invalid, repeat 1, rejected: Cannot analyze command ^GFA,8,8,1,:Z64:/4GBgYGBgf8=:12AA System.IO.InvalidDataException: The archive entry was compressed using an unsupported compression method.
   at System.IO.Compression.Inflater.Inflate(FlushCode flushCode)
   at System.IO.Compression.Inflater.ReadInflateOutput(Byte* bufPtr, Int32 length, FlushCode flushCode, Int32& bytesRead)
   at System.IO.Compression.Inflater.ReadOutput(Byte* bufPtr, Int32 length, Int32& bytesRead)
   at System.IO.Compression.Inflater.InflateVerified(Byte* bufPtr, Int32 length)
   at System.IO.Compression.DeflateStream.CopyToStream.Write(Byte[] buffer, Int32 offset, Int32 count)
   at System.IO.Compression.DeflateStream.CopyToStream.CopyFromSourceToDestination()
   at BinaryKits.Zpl.Label.Helpers.ZebraZ64CompressionHelper.InflateCore(Byte[] data)
   at BinaryKits.Zpl.Label.Helpers.ZebraZ64CompressionHelper.Uncompress(String hexData)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
invalid, repeat 2, rejected: Cannot analyze command ^GFA,8,8,1,:Z64:/4GBgYGBgf8=:12AA System.IO.InvalidDataException: The archive entry was compressed using an unsupported compression method.
   at System.IO.Compression.Inflater.Inflate(FlushCode flushCode)
   at System.IO.Compression.Inflater.ReadInflateOutput(Byte* bufPtr, Int32 length, FlushCode flushCode, Int32& bytesRead)
   at System.IO.Compression.Inflater.ReadOutput(Byte* bufPtr, Int32 length, Int32& bytesRead)
   at System.IO.Compression.Inflater.InflateVerified(Byte* bufPtr, Int32 length)
   at System.IO.Compression.DeflateStream.CopyToStream.Write(Byte[] buffer, Int32 offset, Int32 count)
   at System.IO.Compression.DeflateStream.CopyToStream.CopyFromSourceToDestination()
   at BinaryKits.Zpl.Label.Helpers.ZebraZ64CompressionHelper.InflateCore(Byte[] data)
   at BinaryKits.Zpl.Label.Helpers.ZebraZ64CompressionHelper.Uncompress(String hexData)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
~~~

**BinaryKits.Zpl (.NET) / render: rejected**

~~~text
invalid, repeat 1, rejected: Cannot analyze command ^GFA,8,8,1,:Z64:/4GBgYGBgf8=:12AA System.IO.InvalidDataException: The archive entry was compressed using an unsupported compression method.
   at System.IO.Compression.Inflater.Inflate(FlushCode flushCode)
   at System.IO.Compression.Inflater.ReadInflateOutput(Byte* bufPtr, Int32 length, FlushCode flushCode, Int32& bytesRead)
   at System.IO.Compression.Inflater.ReadOutput(Byte* bufPtr, Int32 length, Int32& bytesRead)
   at System.IO.Compression.Inflater.InflateVerified(Byte* bufPtr, Int32 length)
   at System.IO.Compression.DeflateStream.CopyToStream.Write(Byte[] buffer, Int32 offset, Int32 count)
   at System.IO.Compression.DeflateStream.CopyToStream.CopyFromSourceToDestination()
   at BinaryKits.Zpl.Label.Helpers.ZebraZ64CompressionHelper.InflateCore(Byte[] data)
   at BinaryKits.Zpl.Label.Helpers.ZebraZ64CompressionHelper.Uncompress(String hexData)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
invalid, repeat 2, rejected: Cannot analyze command ^GFA,8,8,1,:Z64:/4GBgYGBgf8=:12AA System.IO.InvalidDataException: The archive entry was compressed using an unsupported compression method.
   at System.IO.Compression.Inflater.Inflate(FlushCode flushCode)
   at System.IO.Compression.Inflater.ReadInflateOutput(Byte* bufPtr, Int32 length, FlushCode flushCode, Int32& bytesRead)
   at System.IO.Compression.Inflater.ReadOutput(Byte* bufPtr, Int32 length, Int32& bytesRead)
   at System.IO.Compression.Inflater.InflateVerified(Byte* bufPtr, Int32 length)
   at System.IO.Compression.DeflateStream.CopyToStream.Write(Byte[] buffer, Int32 offset, Int32 count)
   at System.IO.Compression.DeflateStream.CopyToStream.CopyFromSourceToDestination()
   at BinaryKits.Zpl.Label.Helpers.ZebraZ64CompressionHelper.InflateCore(Byte[] data)
   at BinaryKits.Zpl.Label.Helpers.ZebraZ64CompressionHelper.Uncompress(String hexData)
   at BinaryKits.Zpl.Viewer.Helpers.ImageHelper.GetImageBytes(String dataHex, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
~~~

**ZPLr (TypeScript) / parse: accepted**

~~~text
control, repeat 1, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":60},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
control, repeat 2, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":60},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
invalid, repeat 1, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":56},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
invalid, repeat 2, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":56},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
~~~

**ZPLr (TypeScript) / render: accepted**

### ean-nonnumeric

EAN-13 data contains letters instead of numeric digits. Only tests input rejection, not scanner validity.

Reference: ^BE, guide p. 109. [Valid control](../../../test-data/invalid-zpl/cases/ean-nonnumeric-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/ean-nonnumeric-invalid.zpl)

**codyps/zpl (Rust) / parse: accepted**

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 34, message: "barcode requires decimal digits" }
invalid, repeat 2, rejected: RenderError { offset: 34, message: "barcode requires decimal digits" }
~~~

**zpl-toolchain (Rust) / parse: accepted**

**labelize (Rust) / parse: accepted**

**labelize (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: "EAN-13: need at least 12 digits, got 0"
invalid, repeat 2, rejected: "EAN-13: need at least 12 digits, got 0"
~~~

**zpl-forge (Rust) / parse: accepted**

**zpl-forge (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: BackendError("Barcode Generation Error: IllegalArgumentException - Found empty contents")
invalid, repeat 2, rejected: BackendError("Barcode Generation Error: IllegalArgumentException - Found empty contents")
~~~

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: accepted**

**BinaryKits.Zpl (.NET) / render: rejected**

~~~text
invalid, repeat 1, rejected: System.Exception: Error on zpl element "ABCDEFGHIJKL": Contents should only contain digits, but got 'L'
 ---> System.ArgumentException: Contents should only contain digits, but got 'L'
   at ZXing.OneD.UPCEANReader.getStandardUPCEANChecksum(String s)
   at ZXing.OneD.EAN13Writer.encode(String contents)
   at BinaryKits.Zpl.Viewer.ElementDrawers.BarcodeEAN13ElementDrawer.Draw(ZplElementBase element, DrawerOptions options, SKPoint currentPosition, InternationalFont internationalFont, Int32 printDensityDpmm)
   at BinaryKits.Zpl.Viewer.ZplElementDrawer.DrawMulti(IEnumerable`1 elements, Double labelWidth, Double labelHeight, Int32 printDensityDpmm)
   --- End of inner exception stack trace ---
   at BinaryKits.Zpl.Viewer.ZplElementDrawer.DrawMulti(IEnumerable`1 elements, Double labelWidth, Double labelHeight, Int32 printDensityDpmm)
   at BinaryKits.Zpl.Viewer.ZplElementDrawer.Draw(IEnumerable`1 elements, Double labelWidth, Double labelHeight, Int32 printDensityDpmm)
   at Program.<Main>$(String[] args) in /Volumes/dev/p/zpl-comparison/benchmarks/adapters/dotnet/Program.cs:line 30
invalid, repeat 2, rejected: System.Exception: Error on zpl element "ABCDEFGHIJKL": Contents should only contain digits, but got 'L'
 ---> System.ArgumentException: Contents should only contain digits, but got 'L'
   at ZXing.OneD.UPCEANReader.getStandardUPCEANChecksum(String s)
   at ZXing.OneD.EAN13Writer.encode(String contents)
   at BinaryKits.Zpl.Viewer.ElementDrawers.BarcodeEAN13ElementDrawer.Draw(ZplElementBase element, DrawerOptions options, SKPoint currentPosition, InternationalFont internationalFont, Int32 printDensityDpmm)
   at BinaryKits.Zpl.Viewer.ZplElementDrawer.DrawMulti(IEnumerable`1 elements, Double labelWidth, Double labelHeight, Int32 printDensityDpmm)
   --- End of inner exception stack trace ---
   at BinaryKits.Zpl.Viewer.ZplElementDrawer.DrawMulti(IEnumerable`1 elements, Double labelWidth, Double labelHeight, Int32 printDensityDpmm)
   at BinaryKits.Zpl.Viewer.ZplElementDrawer.Draw(IEnumerable`1 elements, Double labelWidth, Double labelHeight, Int32 printDensityDpmm)
   at Program.<Main>$(String[] args) in /Volumes/dev/p/zpl-comparison/benchmarks/adapters/dotnet/Program.cs:line 30
~~~

**ZPLr (TypeScript) / parse: accepted**

**ZPLr (TypeScript) / render: accepted**

### orientation

Q is outside the N/R/I/B orientation values. Defaulting/ignoring may be intentional; no strict rejection pass/fail.

Reference: ^A. [Valid control](../../../test-data/invalid-zpl/cases/orientation-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/orientation-invalid.zpl)

**codyps/zpl (Rust) / parse: accepted**

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 23, message: "unsupported orientation" }
invalid, repeat 2, rejected: RenderError { offset: 23, message: "unsupported orientation" }
~~~

**zpl-toolchain (Rust) / parse: accepted**

**labelize (Rust) / parse: accepted**

**labelize (Rust) / render: accepted**

**zpl-forge (Rust) / parse: accepted**

**zpl-forge (Rust) / render: accepted**

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: accepted**

**BinaryKits.Zpl (.NET) / render: accepted**

**ZPLr (TypeScript) / parse: accepted**

**ZPLr (TypeScript) / render: accepted**

### negative-width

A box width is negative. Clamping/defaulting may be intentional.

Reference: ^GB. [Valid control](../../../test-data/invalid-zpl/cases/negative-width-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/negative-width-invalid.zpl)

**codyps/zpl (Rust) / parse: accepted**

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 23, message: "invalid shape dimensions" }
invalid, repeat 2, rejected: RenderError { offset: 23, message: "invalid shape dimensions" }
~~~

**zpl-toolchain (Rust) / parse: accepted**

**labelize (Rust) / parse: accepted**

**labelize (Rust) / render: accepted**

**zpl-forge (Rust) / parse: rejected**

~~~text
invalid, repeat 1, rejected: ParseError { line: 1, message: "Invalid or malformed ZPL command (Error code: Digit)" }
invalid, repeat 2, rejected: ParseError { line: 1, message: "Invalid or malformed ZPL command (Error code: Digit)" }
~~~

**zpl-forge (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: ParseError { line: 1, message: "Invalid or malformed ZPL command (Error code: Digit)" }
invalid, repeat 2, rejected: ParseError { line: 1, message: "Invalid or malformed ZPL command (Error code: Digit)" }
~~~

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: accepted**

**BinaryKits.Zpl (.NET) / render: accepted**

**ZPLr (TypeScript) / parse: accepted**

**ZPLr (TypeScript) / render: accepted**

### alignment

Z is outside the field-block alignment values. Defaulting/ignoring may be intentional.

Reference: ^FB. [Valid control](../../../test-data/invalid-zpl/cases/alignment-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/alignment-invalid.zpl)

**codyps/zpl (Rust) / parse: accepted**

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 33, message: "unsupported or invalid field block parameters" }
invalid, repeat 2, rejected: RenderError { offset: 33, message: "unsupported or invalid field block parameters" }
~~~

**zpl-toolchain (Rust) / parse: accepted**

**labelize (Rust) / parse: accepted**

**labelize (Rust) / render: accepted**

**zpl-forge (Rust) / parse: accepted**

**zpl-forge (Rust) / render: accepted**

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: accepted**

**BinaryKits.Zpl (.NET) / render: accepted**

**ZPLr (TypeScript) / parse: accepted**

**ZPLr (TypeScript) / render: accepted**

### field-hex

An enabled field escape contains a nonhex digit. Some APIs preserve malformed escapes literally.

Reference: ^FH. [Valid control](../../../test-data/invalid-zpl/cases/field-hex-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/field-hex-invalid.zpl)

**codyps/zpl (Rust) / parse: accepted**

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 37, message: "invalid hex escape" }
invalid, repeat 2, rejected: RenderError { offset: 37, message: "invalid hex escape" }
~~~

**zpl-toolchain (Rust) / parse: accepted**

**labelize (Rust) / parse: accepted**

**labelize (Rust) / render: accepted**

**zpl-forge (Rust) / parse: accepted**

**zpl-forge (Rust) / render: accepted**

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: accepted**

**BinaryKits.Zpl (.NET) / render: accepted**

**ZPLr (TypeScript) / parse: accepted**

**ZPLr (TypeScript) / render: accepted**

### field-hex-truncated

An enabled field escape has only one hex digit. Some APIs preserve malformed escapes literally.

Reference: ^FH. [Valid control](../../../test-data/invalid-zpl/cases/field-hex-truncated-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/field-hex-truncated-invalid.zpl)

**codyps/zpl (Rust) / parse: accepted**

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 37, message: "truncated field hex escape" }
invalid, repeat 2, rejected: RenderError { offset: 37, message: "truncated field hex escape" }
~~~

**zpl-toolchain (Rust) / parse: accepted**

**labelize (Rust) / parse: accepted**

**labelize (Rust) / render: accepted**

**zpl-forge (Rust) / parse: accepted**

**zpl-forge (Rust) / render: accepted**

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: accepted**

**BinaryKits.Zpl (.NET) / render: accepted**

**ZPLr (TypeScript) / parse: accepted**

**ZPLr (TypeScript) / render: accepted**

### zero-stride

Graphic bytes per row is zero rather than at least one. Observe rejection or recovery separately from malformed encoding.

Reference: ^GF, guide p. 215. [Valid control](../../../test-data/invalid-zpl/cases/zero-stride-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/zero-stride-invalid.zpl)

**codyps/zpl (Rust) / parse: accepted**

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 23, message: "invalid graphic count" }
invalid, repeat 2, rejected: RenderError { offset: 23, message: "invalid graphic count" }
~~~

**zpl-toolchain (Rust) / parse: accepted**

**labelize (Rust) / parse: accepted**

**labelize (Rust) / render: accepted**

**zpl-forge (Rust) / parse: accepted**

**zpl-forge (Rust) / render: execution failure**

~~~text
invalid, repeat 1, crash: thread 'main' (41318073) panicked at /tmp/zpl-comparison-cargo/registry/src/index.crates.io-1949cf8c6b5b557f/zpl-forge-0.3.2/src/forge/png.rs:418:45:
chunk size must be non-zero
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
invalid, repeat 2, crash: thread 'main' (41318075) panicked at /tmp/zpl-comparison-cargo/registry/src/index.crates.io-1949cf8c6b5b557f/zpl-forge-0.3.2/src/forge/png.rs:418:45:
chunk size must be non-zero
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
~~~

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: rejected**

~~~text
invalid, repeat 1, rejected: Cannot analyze command ^GFA,8,8,0,FF818181818181FF System.DivideByZeroException: Attempted to divide by zero.
   at BinaryKits.Zpl.Label.ImageConverters.ImageSharpImageConverter.ConvertImage(Byte[] imageData, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
invalid, repeat 2, rejected: Cannot analyze command ^GFA,8,8,0,FF818181818181FF System.DivideByZeroException: Attempted to divide by zero.
   at BinaryKits.Zpl.Label.ImageConverters.ImageSharpImageConverter.ConvertImage(Byte[] imageData, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
~~~

**BinaryKits.Zpl (.NET) / render: rejected**

~~~text
invalid, repeat 1, rejected: Cannot analyze command ^GFA,8,8,0,FF818181818181FF System.DivideByZeroException: Attempted to divide by zero.
   at BinaryKits.Zpl.Label.ImageConverters.ImageSharpImageConverter.ConvertImage(Byte[] imageData, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
invalid, repeat 2, rejected: Cannot analyze command ^GFA,8,8,0,FF818181818181FF System.DivideByZeroException: Attempted to divide by zero.
   at BinaryKits.Zpl.Label.ImageConverters.ImageSharpImageConverter.ConvertImage(Byte[] imageData, Int32 bytesPerRow)
   at BinaryKits.Zpl.Viewer.CommandAnalyzers.GraphicFieldZplCommandAnalyzer.Analyze(String zplCommand)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.<>c__DisplayClass7_0.<Analyze>b__1(IZplCommandAnalyzer analyzer)
   at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
   at System.Linq.Enumerable.WhereEnumerableIterator`1.MoveNext()
   at System.Collections.Generic.List`1.AddRange(IEnumerable`1 collection)
   at BinaryKits.Zpl.Viewer.ZplAnalyzer.Analyze(String zplData)
~~~

**ZPLr (TypeScript) / parse: accepted**

~~~text
control, repeat 1, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":50},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
control, repeat 2, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":50},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
invalid, repeat 1, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":50},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
invalid, repeat 2, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^GF is supported with limitations: Zebra compressed-binary (C) payloads are diagnosed but not decoded.","span":{"start":23,"end":50},"severity":"info","command":"^GF","phase":"parse","labelIndex":0}
~~~

**ZPLr (TypeScript) / render: accepted**

### qr-model

QR model 3 is outside the supported model values. Defaulting/ignoring may be intentional.

Reference: ^BQ. [Valid control](../../../test-data/invalid-zpl/cases/qr-model-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/qr-model-invalid.zpl)

**codyps/zpl (Rust) / parse: accepted**

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 35, message: "BQ: parameter 2 mode unsupported" }
invalid, repeat 2, rejected: RenderError { offset: 35, message: "BQ: parameter 2 mode unsupported" }
~~~

**zpl-toolchain (Rust) / parse: accepted**

**labelize (Rust) / parse: accepted**

**labelize (Rust) / render: accepted**

**zpl-forge (Rust) / parse: accepted**

**zpl-forge (Rust) / render: accepted**

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: accepted**

**BinaryKits.Zpl (.NET) / render: accepted**

**ZPLr (TypeScript) / parse: accepted**

**ZPLr (TypeScript) / render: accepted**

### qr-mask

QR mask 8 is outside the 0..7 range. Defaulting/ignoring may be intentional.

Reference: ^BQ. [Valid control](../../../test-data/invalid-zpl/cases/qr-mask-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/qr-mask-invalid.zpl)

**codyps/zpl (Rust) / parse: accepted**

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 35, message: "BQ: parameter 5 out of range" }
invalid, repeat 2, rejected: RenderError { offset: 35, message: "BQ: parameter 5 out of range" }
~~~

**zpl-toolchain (Rust) / parse: accepted**

**labelize (Rust) / parse: accepted**

**labelize (Rust) / render: accepted**

**zpl-forge (Rust) / parse: accepted**

**zpl-forge (Rust) / render: accepted**

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: accepted**

**BinaryKits.Zpl (.NET) / render: accepted**

**ZPLr (TypeScript) / parse: accepted**

**ZPLr (TypeScript) / render: accepted**

### encoding

Character encoding 999 is outside the documented selections. Defaulting/ignoring may be intentional.

Reference: ^CI. [Valid control](../../../test-data/invalid-zpl/cases/encoding-control.zpl) · [Modified input](../../../test-data/invalid-zpl/cases/encoding-invalid.zpl)

**codyps/zpl (Rust) / parse: accepted**

**codyps/zpl (Rust) / render: rejected**

~~~text
invalid, repeat 1, rejected: RenderError { offset: 23, message: "character encoding unsupported" }
invalid, repeat 2, rejected: RenderError { offset: 23, message: "character encoding unsupported" }
~~~

**zpl-toolchain (Rust) / parse: accepted**

**labelize (Rust) / parse: accepted**

**labelize (Rust) / render: accepted**

**zpl-forge (Rust) / parse: accepted**

**zpl-forge (Rust) / render: accepted**

**go-zpl (Go) / parse: accepted**

**go-zpl (Go) / render: accepted**

**zpl-rs (Rust → Go) / render: accepted**

**BinaryKits.Zpl (.NET) / parse: accepted**

**BinaryKits.Zpl (.NET) / render: accepted**

**ZPLr (TypeScript) / parse: accepted**

~~~text
control, repeat 1, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^CI is supported with limitations: Table-specific EUC-CN and non-GB18030 ^CI16/^CI26 variants are not inferred without a compatible downloaded mapping; standard Unicode, Western, Shift-JIS, EUC-JP, and GB18030 paths are implemented.","span":{"start":23,"end":28},"severity":"info","command":"^CI","phase":"parse","labelIndex":0}
control, repeat 2, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^CI is supported with limitations: Table-specific EUC-CN and non-GB18030 ^CI16/^CI26 variants are not inferred without a compatible downloaded mapping; standard Unicode, Western, Shift-JIS, EUC-JP, and GB18030 paths are implemented.","span":{"start":23,"end":28},"severity":"info","command":"^CI","phase":"parse","labelIndex":0}
invalid, repeat 1, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^CI is supported with limitations: Table-specific EUC-CN and non-GB18030 ^CI16/^CI26 variants are not inferred without a compatible downloaded mapping; standard Unicode, Western, Shift-JIS, EUC-JP, and GB18030 paths are implemented.","span":{"start":23,"end":29},"severity":"info","command":"^CI","phase":"parse","labelIndex":0}
invalid, repeat 2, accepted: {"code":"PARTIALLY_SUPPORTED_COMMAND","message":"^CI is supported with limitations: Table-specific EUC-CN and non-GB18030 ^CI16/^CI26 variants are not inferred without a compatible downloaded mapping; standard Unicode, Western, Shift-JIS, EUC-JP, and GB18030 paths are implemented.","span":{"start":23,"end":29},"severity":"info","command":"^CI","phase":"parse","labelIndex":0}
~~~

**ZPLr (TypeScript) / render: accepted**
