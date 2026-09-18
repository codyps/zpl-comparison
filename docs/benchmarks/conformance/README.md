# Rendering conformance run

Suite: `render-conformance-v1`. 4 cases; 7 adapters.

This reports execution and equal-image relationships, not printer accuracy unless hash-matched printer references were supplied. A rendered image can still be wrong. Font coverage is device-dependent. Invalid inputs are kept separate.

| Library | Valid/boundary cases | Nonblank | Blank | Errors | Crashes | Timeouts | Printer IoU |
| --- | --- | --- | --- | --- | --- | --- | --- |
| codyps/zpl (Rust) | 4 | 0 | 0 | 4 | 0 | 0 | N/A |
| labelize (Rust) | 4 | 4 | 0 | 0 | 0 | 0 | N/A |
| zpl-forge (Rust) | 4 | 4 | 0 | 0 | 0 | 0 | N/A |
| go-zpl (Go) | 4 | 4 | 0 | 0 | 0 | 0 | N/A |
| zpl-rs (Rust → Go) | 4 | 4 | 0 | 0 | 0 | 0 | N/A |
| BinaryKits.Zpl (.NET) | 4 | 4 | 0 | 0 | 0 | 0 | N/A |
| ZPLr (TypeScript) | 4 | 4 | 0 | 0 | 0 | 0 | N/A |


## Equal-raster relationships

Equality requires at least two nonblank successful outputs. Both blanks/errors are inconclusive; equality alone is not printer fidelity.

| Library | Relationship | Outcome |
| --- | --- | --- |


## Individual cases

### valid

| Case | codyps/zpl (Rust) | labelize (Rust) | zpl-forge (Rust) | go-zpl (Go) | zpl-rs (Rust → Go) | BinaryKits.Zpl (.NET) | ZPLr (TypeScript) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| torture-typography | error | [rendered](images/torture-typography-labelize.png) | [rendered](images/torture-typography-forge.png) | [rendered](images/torture-typography-go.png) | [rendered](images/torture-typography-ffi.png) | [rendered](images/torture-typography-binarykits.png) | [rendered](images/torture-typography-zplr.png) |
| torture-geometry | error | [rendered](images/torture-geometry-labelize.png) | [rendered](images/torture-geometry-forge.png) | [rendered](images/torture-geometry-go.png) | [rendered](images/torture-geometry-ffi.png) | [rendered](images/torture-geometry-binarykits.png) | [rendered](images/torture-geometry-zplr.png) |
| torture-shipping-label | error | [rendered](images/torture-shipping-label-labelize.png) | [rendered](images/torture-shipping-label-forge.png) | [rendered](images/torture-shipping-label-go.png) | [rendered](images/torture-shipping-label-ffi.png) | [rendered](images/torture-shipping-label-binarykits.png) | [rendered](images/torture-shipping-label-zplr.png) |
| torture-overlap | error | [rendered](images/torture-overlap-labelize.png) | [rendered](images/torture-overlap-forge.png) | [rendered](images/torture-overlap-go.png) | [rendered](images/torture-overlap-ffi.png) | [rendered](images/torture-overlap-binarykits.png) | [rendered](images/torture-overlap-zplr.png) |
