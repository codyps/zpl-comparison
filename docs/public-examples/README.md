# Public examples against the ZD621

22 labels: 17 rendered, 5 pixel-exact full canvases, 5 render failures. Measured 2026-10-02T13:33:14Z using zpl 6aa0435f057f048f0b238e2f86ea06e8de4d12e0 with zpl::render::profiles::ZD621_203_DPI. Printer: ZTC ZD621-203dpi ZPL, V93.21.33Z, 203 dpi.

[Interactive gallery](index.html) · [Sources, adaptations and reproduction](../../test-data/public-zpl/README.md) · [Capture provenance](../../references/public-zd621-20261002/manifest.json) · [Results](results.json)

HTTP Preview Label captures; no physical print/scan. The start/end control matches. Compare complete native canvases at the original origin, threshold 128; no alignment, padding, cropping or rescaling. IoU measures foreground intersection/union, not white-background agreement. Magenta is printer-only ink (underpaint); cyan is renderer-only ink (overpaint). Whole-label IoU is not a per-text-field score or proof of barcode decoding/symbol parity. Blank references and unequal canvases are unscored. Other libraries were not measured in this campaign.

| Document | Status | Foreground IoU | Underpaint | Overpaint |
| --- | --- | ---: | ---: | ---: |
| [labelixa-carrier-style-shipping-4x6](index.html#labelixa-carrier-style-shipping-4x6) | rendered | 76.908% | 19686 | 23499 |
| [labelixa-datamatrix-serial-1x1](index.html#labelixa-datamatrix-serial-1x1) | exact | 100.000% | 0 | 0 |
| [labelixa-fba-fnsku-product-2x1](index.html#labelixa-fba-fnsku-product-2x1) | rendered | 87.598% | 864 | 938 |
| [labelixa-gs1-128-sscc-shipping-4x6](index.html#labelixa-gs1-128-sscc-shipping-4x6) | rendered | 88.453% | 8857 | 9646 |
| [labelixa-multi-label-batch-2x1-page-1](index.html#labelixa-multi-label-batch-2x1-page-1) | exact | 100.000% | 0 | 0 |
| [labelixa-multi-label-batch-2x1-page-2](index.html#labelixa-multi-label-batch-2x1-page-2) | exact | 100.000% | 0 | 0 |
| [labelixa-multi-label-batch-2x1-page-3](index.html#labelixa-multi-label-batch-2x1-page-3) | exact | 100.000% | 0 | 0 |
| [labelixa-pallet-license-plate-4x3](index.html#labelixa-pallet-license-plate-4x3) | rendered | 93.423% | 2771 | 4214 |
| [labelixa-product-label-ean13-2x1](index.html#labelixa-product-label-ean13-2x1) | rendered | 96.173% | 245 | 243 |
| [labelixa-qr-url-2x2](index.html#labelixa-qr-url-2x2) | rendered | 37.249% | 17974 | 12145 |
| [labelixa-shelf-label-3x1](index.html#labelixa-shelf-label-3x1) | exact | 100.000% | 0 | 0 |
| [labelixa-shipping-label-4x6](index.html#labelixa-shipping-label-4x6) | rendered | 92.026% | 4621 | 4892 |
| [labelixa-shopify-product-label-2x1](index.html#labelixa-shopify-product-label-2x1) | rendered | 77.652% | 1638 | 1709 |
| [binarykits-example1-102x152](index.html#binarykits-example1-102x152) | rendered | 95.542% | 3530 | 3019 |
| [binarykits-example1-54x86](index.html#binarykits-example1-54x86) | rendered | 91.211% | 2674 | 2739 |
| [binarykits-example2-102x170](index.html#binarykits-example2-102x170) | error | unscored | — | — |
| [binarykits-example3-54x86](index.html#binarykits-example3-54x86) | rendered | 88.699% | 3089 | 4426 |
| [binarykits-example4-102x152](index.html#binarykits-example4-102x152) | error | unscored | — | — |
| [binarykits-example5-75x202](index.html#binarykits-example5-75x202) | error | unscored | — | — |
| [binarykits-example6-75x254](index.html#binarykits-example6-75x254) | error | unscored | — | — |
| [binarykits-example8-64x152](index.html#binarykits-example8-64x152) | error | unscored | — | — |
| [binarykits-example9-102x152](index.html#binarykits-example9-102x152) | rendered | 92.703% | 5874 | 6683 |

See [findings](FINDINGS.md) for source diagnostics and limits.
