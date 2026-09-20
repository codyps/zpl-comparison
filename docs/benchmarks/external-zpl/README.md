# Rendering conformance run

[External printer/render/difference gallery](../accuracy/comparisons/external/README.md)

Suite: `external-zpl-v1`. 8 cases; 8 adapters.

This reports execution and equal-image relationships, not printer accuracy unless hash-matched printer references were supplied. A rendered image can still be wrong. Font coverage is device-dependent. Invalid inputs are kept separate.

## Imported examples

Unmodified upstream inputs, including stateful and printer-configuration examples, run offline only. Boundary classification means unverified example semantics, not certified valid ZPL. Upstream library fixtures are not an independent holdout.

| Fixture | Group | Canvas (dots) | Pinned source |
| --- | --- | --- | --- |
| [zpl-toolchain-shipping_label](../../../test-data/external-zpl/cases/zpl-toolchain-shipping_label.zpl) | shipping | 812×1218 | [upstream](https://github.com/trevordcampbell/zpl-toolchain/blob/3da58518c1013fffd46d2147b0927a1d5b4aeab5/samples/shipping_label.zpl) |
| [zpl-toolchain-product_label](../../../test-data/external-zpl/cases/zpl-toolchain-product_label.zpl) | product | 609×406 | [upstream](https://github.com/trevordcampbell/zpl-toolchain/blob/3da58518c1013fffd46d2147b0927a1d5b4aeab5/samples/product_label.zpl) |
| [zpl-toolchain-warehouse_label](../../../test-data/external-zpl/cases/zpl-toolchain-warehouse_label.zpl) | warehouse | 812×609 | [upstream](https://github.com/trevordcampbell/zpl-toolchain/blob/3da58518c1013fffd46d2147b0927a1d5b4aeab5/samples/warehouse_label.zpl) |
| [zpl-toolchain-compliance_label](../../../test-data/external-zpl/cases/zpl-toolchain-compliance_label.zpl) | compliance | 812×1218 | [upstream](https://github.com/trevordcampbell/zpl-toolchain/blob/3da58518c1013fffd46d2147b0927a1d5b4aeab5/samples/compliance_label.zpl) |
| [zpl-toolchain-usps_surepost_sample](../../../test-data/external-zpl/cases/zpl-toolchain-usps_surepost_sample.zpl) | printer-configuration | 812×1524 | [upstream](https://github.com/trevordcampbell/zpl-toolchain/blob/3da58518c1013fffd46d2147b0927a1d5b4aeab5/samples/usps_surepost_sample.zpl) |
| [zplr-asset-matrix-pdf417](../../../test-data/external-zpl/cases/zplr-asset-matrix-pdf417.zpl) | asset | 900×500 | [upstream](https://github.com/le2ni/zplr/blob/1c94eadfc5afb494b4c92dd10ad4808bd3d19529/fixtures/asset-matrix-pdf417.zpl) |
| [zplr-retail-upc-ean](../../../test-data/external-zpl/cases/zplr-retail-upc-ean.zpl) | retail | 800×500 | [upstream](https://github.com/le2ni/zplr/blob/1c94eadfc5afb494b4c92dd10ad4808bd3d19529/fixtures/retail-upc-ean.zpl) |
| [zplr-stored-resources](../../../test-data/external-zpl/cases/zplr-stored-resources.zpl) | stateful | 420×220 | [upstream](https://github.com/le2ni/zplr/blob/1c94eadfc5afb494b4c92dd10ad4808bd3d19529/fixtures/stored-resources.zpl) |

| Library | Valid/boundary cases | Nonblank | Blank | Errors | Crashes | Timeouts | Printer IoU |
| --- | --- | --- | --- | --- | --- | --- | --- |
| codyps/zpl (Rust) | 8 | 5 | 0 | 3 | 0 | 0 | N/A |
| labelize (Rust) | 8 | 8 | 0 | 0 | 0 | 0 | N/A |
| zpl-forge (Rust) | 8 | 6 | 0 | 2 | 0 | 0 | N/A |
| go-zpl (Go) | 8 | 8 | 0 | 0 | 0 | 0 | N/A |
| zpl-rs (Rust → Go) | 8 | 8 | 0 | 0 | 0 | 0 | N/A |
| BinaryKits.Zpl (.NET) | 8 | 7 | 0 | 0 | 1 | 0 | N/A |
| ZPLr (TypeScript) | 8 | 8 | 0 | 0 | 0 | 0 | N/A |
| Labelary (SaaS) | 8 | 8 | 0 | 0 | 0 | 0 | N/A |


## Equal-raster relationships

Equality requires at least two nonblank successful outputs. Both blanks/errors are inconclusive; equality alone is not printer fidelity.

| Library | Relationship | Outcome |
| --- | --- | --- |


## Individual cases

### boundary

| Case | codyps/zpl (Rust) | labelize (Rust) | zpl-forge (Rust) | go-zpl (Go) | zpl-rs (Rust → Go) | BinaryKits.Zpl (.NET) | ZPLr (TypeScript) | Labelary (SaaS) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [zpl-toolchain-shipping_label](../accuracy/comparisons/external/cases/zpl-toolchain-shipping_label.md) | [rendered](images/zpl-toolchain-shipping_label-codyps-zpl.png) | [rendered](images/zpl-toolchain-shipping_label-labelize.png) | [rendered](images/zpl-toolchain-shipping_label-forge.png) | [rendered](images/zpl-toolchain-shipping_label-go.png) | [rendered](images/zpl-toolchain-shipping_label-ffi.png) | [rendered](images/zpl-toolchain-shipping_label-binarykits.png) | [rendered](images/zpl-toolchain-shipping_label-zplr.png) | [rendered](images/zpl-toolchain-shipping_label-labelary.png) |
| [zpl-toolchain-product_label](../accuracy/comparisons/external/cases/zpl-toolchain-product_label.md) | [rendered](images/zpl-toolchain-product_label-codyps-zpl.png) | [rendered](images/zpl-toolchain-product_label-labelize.png) | [rendered](images/zpl-toolchain-product_label-forge.png) | [rendered](images/zpl-toolchain-product_label-go.png) | [rendered](images/zpl-toolchain-product_label-ffi.png) | [rendered](images/zpl-toolchain-product_label-binarykits.png) | [rendered](images/zpl-toolchain-product_label-zplr.png) | [rendered](images/zpl-toolchain-product_label-labelary.png) |
| [zpl-toolchain-warehouse_label](../accuracy/comparisons/external/cases/zpl-toolchain-warehouse_label.md) | [rendered](images/zpl-toolchain-warehouse_label-codyps-zpl.png) | [rendered](images/zpl-toolchain-warehouse_label-labelize.png) | [rendered](images/zpl-toolchain-warehouse_label-forge.png) | [rendered](images/zpl-toolchain-warehouse_label-go.png) | [rendered](images/zpl-toolchain-warehouse_label-ffi.png) | [rendered](images/zpl-toolchain-warehouse_label-binarykits.png) | [rendered](images/zpl-toolchain-warehouse_label-zplr.png) | [rendered](images/zpl-toolchain-warehouse_label-labelary.png) |
| [zpl-toolchain-compliance_label](../accuracy/comparisons/external/cases/zpl-toolchain-compliance_label.md) | [rendered](images/zpl-toolchain-compliance_label-codyps-zpl.png) | [rendered](images/zpl-toolchain-compliance_label-labelize.png) | [rendered](images/zpl-toolchain-compliance_label-forge.png) | [rendered](images/zpl-toolchain-compliance_label-go.png) | [rendered](images/zpl-toolchain-compliance_label-ffi.png) | [rendered](images/zpl-toolchain-compliance_label-binarykits.png) | [rendered](images/zpl-toolchain-compliance_label-zplr.png) | [rendered](images/zpl-toolchain-compliance_label-labelary.png) |
| [zpl-toolchain-usps_surepost_sample](../accuracy/comparisons/external/cases/zpl-toolchain-usps_surepost_sample.md) | error | [rendered](images/zpl-toolchain-usps_surepost_sample-labelize.png) | error | [rendered](images/zpl-toolchain-usps_surepost_sample-go.png) | [rendered](images/zpl-toolchain-usps_surepost_sample-ffi.png) | [rendered](images/zpl-toolchain-usps_surepost_sample-binarykits.png) | [rendered](images/zpl-toolchain-usps_surepost_sample-zplr.png) | [rendered](images/zpl-toolchain-usps_surepost_sample-labelary.png) |
| [zplr-asset-matrix-pdf417](../accuracy/comparisons/external/cases/zplr-asset-matrix-pdf417.md) | [rendered](images/zplr-asset-matrix-pdf417-codyps-zpl.png) | [rendered](images/zplr-asset-matrix-pdf417-labelize.png) | [rendered](images/zplr-asset-matrix-pdf417-forge.png) | [rendered](images/zplr-asset-matrix-pdf417-go.png) | [rendered](images/zplr-asset-matrix-pdf417-ffi.png) | [rendered](images/zplr-asset-matrix-pdf417-binarykits.png) | [rendered](images/zplr-asset-matrix-pdf417-zplr.png) | [rendered](images/zplr-asset-matrix-pdf417-labelary.png) |
| [zplr-retail-upc-ean](../accuracy/comparisons/external/cases/zplr-retail-upc-ean.md) | error | [rendered](images/zplr-retail-upc-ean-labelize.png) | [rendered](images/zplr-retail-upc-ean-forge.png) | [rendered](images/zplr-retail-upc-ean-go.png) | [rendered](images/zplr-retail-upc-ean-ffi.png) | [rendered](images/zplr-retail-upc-ean-binarykits.png) | [rendered](images/zplr-retail-upc-ean-zplr.png) | [rendered](images/zplr-retail-upc-ean-labelary.png) |
| [zplr-stored-resources](../accuracy/comparisons/external/cases/zplr-stored-resources.md) | error | [rendered](images/zplr-stored-resources-labelize.png) | error | [rendered](images/zplr-stored-resources-go.png) | [rendered](images/zplr-stored-resources-ffi.png) | crashed | [rendered](images/zplr-stored-resources-zplr.png) | [rendered](images/zplr-stored-resources-labelary.png) |
