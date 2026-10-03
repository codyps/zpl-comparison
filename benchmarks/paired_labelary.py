#!/usr/bin/env python3
"""Capture/replay Labelary for the paired campaign's exact ZD621 inputs.

The paired ZQ610 inputs already have responses in zq610-candidates/labelary.
Network access occurs only with --capture; normal builds validate saved bytes.
"""
import argparse
import json
from pathlib import Path

import labelary

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "references/paired-labelary"


def inputs():
    root = "references/zq610-plus-v1/"
    manifest = json.loads((ROOT / root / "manifest.json").read_text())
    rows = []
    for name, case in manifest["cases"].items():
        status = case["status"].get("zd621", {})
        if status.get("status") != "captured":
            continue
        width, height = status["measurement"]["dimensions"]
        rows.append(dict(suite="paired-zd621", name=name, source=root + name + "/zd621.zpl",
                         sha256=status["submitted_sha256"], width=width, height=height, validity="valid"))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true")
    args = parser.parse_args()
    labelary.inputs = inputs
    if args.capture:
        labelary.capture(OUTPUT, extend=(OUTPUT / "captures.json").exists())
    data = labelary.validate(OUTPUT)
    print("Verified", len(data["cases"]), "paired Labelary responses")


if __name__ == "__main__":
    main()
