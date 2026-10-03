#!/usr/bin/env python3
"""Optional independent decoder audit; not a runtime renderer dependency.

Reproduce with zxing-cpp==3.1.1 and Pillow==12.3.0. A successful decode
establishes payload evidence only, not printer pixel parity. An empty decoder
result is not proof that no valid barcode exists.
"""

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

from PIL import Image
import zxingcpp

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    "labelixa-qr-url-2x2", "labelixa-carrier-style-shipping-4x6",
    "binarykits-example4-102x152", "binarykits-example5-75x202",
    "binarykits-example6-75x254", "binarykits-example8-64x152",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if version("zxing-cpp") != "3.1.1":
        raise ValueError("Use the recorded zxing-cpp 3.1.1 decoder")
    rows = []
    campaign = json.loads((ROOT / "docs/public-examples/results.json").read_text())
    if campaign.get("schema") == 2:
        inputs = [(c["name"], "printer", c["reference"], "rendered", "") for c in campaign["cases"]]
        inputs += [(r["case"], r["library"], r.get("image"), r["status"], r.get("diagnostic", "")) for r in campaign["results"]]
    else:
        inputs = [(name, kind, directory + "/" + prefix + name + ".png", "rendered", "") for name in CASES
                  for kind, directory, prefix in [("printer", "references/public-zd621-20261002", ""),
                                                  ("zpl", "docs/public-examples/images", ""),
                                                  ("labelary", "docs/benchmarks/labelary/images", "public-zpl--")]]
    for name, kind, relative, status, diagnostic in inputs:
        if not relative:
            rows.append(dict(case=name, kind=kind, status=status, diagnostic=diagnostic, symbols=[]))
            continue
        path = ROOT / relative
        if not path.exists():
            if campaign.get("schema") == 2:
                raise ValueError("Missing decoder input: " + str(path))
            continue
        with Image.open(path) as image:
            symbols = [dict(format=str(s.format), text=s.text, bytes_hex=s.bytes.hex(),
                            position=str(s.position), valid=s.valid)
                       for s in zxingcpp.read_barcodes(image)]
        rows.append(dict(case=name, kind=kind, file=str(path.relative_to(ROOT)),
                         png_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), symbols=symbols))
    data = dict(decoder="zxing-cpp 3.1.1", pillow=version("pillow"), results=rows)
    path = ROOT / "docs/public-examples/barcodes.json"
    if args.check:
        if json.loads(path.read_text()) != data:
            raise ValueError("Barcode audit changed")
    else:
        path.write_text(json.dumps(data, indent=2) + "\n")
    print("Verified independent barcode audit" if args.check else "Recorded independent barcode audit")


if __name__ == "__main__":
    main()
