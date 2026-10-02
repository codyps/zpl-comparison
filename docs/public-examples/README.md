# Public examples against the ZD621

zpl: 22 labels, 17 rendered, 5 pixel-exact full canvases, 5 render failures. Measured 2026-10-02T13:33:14Z using zpl 6aa0435f057f048f0b238e2f86ea06e8de4d12e0 with zpl::render::profiles::ZD621_203_DPI. Printer: ZTC ZD621-203dpi ZPL, V93.21.33Z, 203 dpi. Labelary: 22 rendered, 0 pixel-exact full canvases. Captured 2026-10-02T14:05:56+00:00 through 2026-10-02T14:06:11+00:00; UTC capture timestamps; no renderer version exposed.

[Interactive gallery](index.html) · [Sources, adaptations and reproduction](../../test-data/public-zpl/README.md) · [Capture provenance](../../references/public-zd621-20261002/manifest.json) · [zpl results](results.json) · [Labelary results](labelary-results.json) · [Service responses](../benchmarks/labelary/captures.json)

HTTP Preview Label captures; no physical print/scan. The start/end control matches. Compare complete native canvases at the original origin, threshold 128; no alignment, padding, cropping or rescaling. IoU measures foreground intersection/union, not white-background agreement. Magenta is printer-only ink (underpaint); cyan is renderer-only ink (overpaint). Whole-label IoU is not a per-text-field score or proof of barcode decoding/symbol parity. Blank references and unequal canvases are unscored. Labelary is another renderer; the printer remains the reference. Other libraries were not measured in this campaign.

| Document | Renderer | Status | Foreground IoU | Underpaint | Overpaint |
| --- | --- | --- | ---: | ---: | ---: |
| [labelixa-carrier-style-shipping-4x6](index.html#labelixa-carrier-style-shipping-4x6) | zpl | rendered | 76.908% | 19686 | 23499 |
| [labelixa-carrier-style-shipping-4x6](index.html#labelixa-carrier-style-shipping-4x6) | Labelary | rendered | 86.058% | 12560 | 11895 |
| [labelixa-datamatrix-serial-1x1](index.html#labelixa-datamatrix-serial-1x1) | zpl | exact | 100.000% | 0 | 0 |
| [labelixa-datamatrix-serial-1x1](index.html#labelixa-datamatrix-serial-1x1) | Labelary | rendered | 84.830% | 405 | 367 |
| [labelixa-fba-fnsku-product-2x1](index.html#labelixa-fba-fnsku-product-2x1) | zpl | rendered | 87.598% | 864 | 938 |
| [labelixa-fba-fnsku-product-2x1](index.html#labelixa-fba-fnsku-product-2x1) | Labelary | rendered | 85.822% | 1068 | 1001 |
| [labelixa-gs1-128-sscc-shipping-4x6](index.html#labelixa-gs1-128-sscc-shipping-4x6) | zpl | rendered | 88.453% | 8857 | 9646 |
| [labelixa-gs1-128-sscc-shipping-4x6](index.html#labelixa-gs1-128-sscc-shipping-4x6) | Labelary | rendered | 87.089% | 10873 | 9840 |
| [labelixa-multi-label-batch-2x1-page-1](index.html#labelixa-multi-label-batch-2x1-page-1) | zpl | exact | 100.000% | 0 | 0 |
| [labelixa-multi-label-batch-2x1-page-1](index.html#labelixa-multi-label-batch-2x1-page-1) | Labelary | rendered | 93.502% | 411 | 384 |
| [labelixa-multi-label-batch-2x1-page-2](index.html#labelixa-multi-label-batch-2x1-page-2) | zpl | exact | 100.000% | 0 | 0 |
| [labelixa-multi-label-batch-2x1-page-2](index.html#labelixa-multi-label-batch-2x1-page-2) | Labelary | rendered | 93.550% | 430 | 385 |
| [labelixa-multi-label-batch-2x1-page-3](index.html#labelixa-multi-label-batch-2x1-page-3) | zpl | exact | 100.000% | 0 | 0 |
| [labelixa-multi-label-batch-2x1-page-3](index.html#labelixa-multi-label-batch-2x1-page-3) | Labelary | rendered | 93.219% | 440 | 374 |
| [labelixa-pallet-license-plate-4x3](index.html#labelixa-pallet-license-plate-4x3) | zpl | rendered | 93.423% | 2771 | 4214 |
| [labelixa-pallet-license-plate-4x3](index.html#labelixa-pallet-license-plate-4x3) | Labelary | rendered | 88.187% | 5962 | 6902 |
| [labelixa-product-label-ean13-2x1](index.html#labelixa-product-label-ean13-2x1) | zpl | rendered | 96.173% | 245 | 243 |
| [labelixa-product-label-ean13-2x1](index.html#labelixa-product-label-ean13-2x1) | Labelary | rendered | 83.219% | 1181 | 1103 |
| [labelixa-qr-url-2x2](index.html#labelixa-qr-url-2x2) | zpl | rendered | 37.249% | 17974 | 12145 |
| [labelixa-qr-url-2x2](index.html#labelixa-qr-url-2x2) | Labelary | rendered | 34.410% | 19111 | 12801 |
| [labelixa-shelf-label-3x1](index.html#labelixa-shelf-label-3x1) | zpl | exact | 100.000% | 0 | 0 |
| [labelixa-shelf-label-3x1](index.html#labelixa-shelf-label-3x1) | Labelary | rendered | 95.126% | 518 | 586 |
| [labelixa-shipping-label-4x6](index.html#labelixa-shipping-label-4x6) | zpl | rendered | 92.026% | 4621 | 4892 |
| [labelixa-shipping-label-4x6](index.html#labelixa-shipping-label-4x6) | Labelary | rendered | 88.583% | 7345 | 6454 |
| [labelixa-shopify-product-label-2x1](index.html#labelixa-shopify-product-label-2x1) | zpl | rendered | 77.652% | 1638 | 1709 |
| [labelixa-shopify-product-label-2x1](index.html#labelixa-shopify-product-label-2x1) | Labelary | rendered | 79.099% | 1551 | 1545 |
| [binarykits-example1-102x152](index.html#binarykits-example1-102x152) | zpl | rendered | 95.542% | 3530 | 3019 |
| [binarykits-example1-102x152](index.html#binarykits-example1-102x152) | Labelary | rendered | 91.612% | 6994 | 5538 |
| [binarykits-example1-54x86](index.html#binarykits-example1-54x86) | zpl | rendered | 91.211% | 2674 | 2739 |
| [binarykits-example1-54x86](index.html#binarykits-example1-54x86) | Labelary | rendered | 88.489% | 3757 | 3409 |
| [binarykits-example2-102x170](index.html#binarykits-example2-102x170) | zpl | error | unscored | — | — |
| [binarykits-example2-102x170](index.html#binarykits-example2-102x170) | Labelary | rendered | 79.499% | 16691 | 19673 |
| [binarykits-example3-54x86](index.html#binarykits-example3-54x86) | zpl | rendered | 88.699% | 3089 | 4426 |
| [binarykits-example3-54x86](index.html#binarykits-example3-54x86) | Labelary | rendered | 93.352% | 1721 | 2577 |
| [binarykits-example4-102x152](index.html#binarykits-example4-102x152) | zpl | error | unscored | — | — |
| [binarykits-example4-102x152](index.html#binarykits-example4-102x152) | Labelary | rendered | 78.864% | 17138 | 16315 |
| [binarykits-example5-75x202](index.html#binarykits-example5-75x202) | zpl | error | unscored | — | — |
| [binarykits-example5-75x202](index.html#binarykits-example5-75x202) | Labelary | rendered | 89.884% | 5793 | 6372 |
| [binarykits-example6-75x254](index.html#binarykits-example6-75x254) | zpl | error | unscored | — | — |
| [binarykits-example6-75x254](index.html#binarykits-example6-75x254) | Labelary | rendered | 60.691% | 32480 | 24641 |
| [binarykits-example8-64x152](index.html#binarykits-example8-64x152) | zpl | error | unscored | — | — |
| [binarykits-example8-64x152](index.html#binarykits-example8-64x152) | Labelary | rendered | 75.032% | 8881 | 8007 |
| [binarykits-example9-102x152](index.html#binarykits-example9-102x152) | zpl | rendered | 92.703% | 5874 | 6683 |
| [binarykits-example9-102x152](index.html#binarykits-example9-102x152) | Labelary | rendered | 91.700% | 7487 | 6807 |

See [findings](FINDINGS.md) for source diagnostics and limits.
