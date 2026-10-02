#!/usr/bin/env python3
"""Reproduce reviewed preview variants from pinned, byte-preserved public sources.

Source URLs, revisions, licenses and hashes are in sources.json. No network calls.
Zebra command authority: ../../docs/zpl-command-index.tsv (^PW, ^LL, ^XA/^XZ).
Dimensions are source dots (Labelixa) or 8 dots/mm from BinaryKits filenames.
Only the canvas and a leading UTF-8 BOM change; batch pages are separated.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifacts():
    sources = json.loads((HERE / "sources.json").read_text())
    spec = importlib.util.spec_from_file_location(
        "content_scope", HERE.parent / "render-conformance/generate.py"
    )
    scope = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scope)
    cases, files = [], {}
    for source in sources["sources"]:
        original = (HERE / source["file"]).read_bytes()
        assert sha(original) == source["sha256"], source["file"]
        assert sha((HERE / source["license"]).read_bytes()) == source["license_sha256"]
        body = original.removeprefix(b"\xef\xbb\xbf")
        pages = re.findall(rb"\^XA.*?\^XZ", body, re.S)
        assert len(pages) == source["pages"]
        assert b"".join(body.split()) == b"".join(b"".join(pages).split())
        for number, page in enumerate(pages, 1):
            name = source["name"]
            changes = []
            if original.startswith(b"\xef\xbb\xbf"):
                changes.append("Remove the leading UTF-8 BOM before ^XA")
            if len(pages) > 1:
                name += f"-page-{number}"
                changes.append(f"Extract format {number} of {len(pages)}; no multi-page support claim")
            width, height = source["width"], source["height"]
            if re.search(rb"\^PW\d+", page):
                page, count = re.subn(rb"\^PW\d+", f"^PW{width}".encode(), page)
                assert count == 1
                changes.append(f"Set ^PW{width} to the next 64-dot native preview width")
            else:
                page = page[:3] + f"^PW{width}^LL{height}".encode() + page[3:]
                changes.append(f"Insert ^PW{width}^LL{height}; size from upstream filename at 8 dots/mm, width rounded up to 64 dots")
            assert re.findall(rb"\^LL(\d+)", page) == [str(height).encode()]
            page += b"\n"
            changes.append("Normalize only whitespace outside the selected format to one final newline")
            file = f"cases/{name}.zpl"
            files[file] = page
            cases.append(dict(
                name=name, group=source["group"], file=file, sha256=sha(page),
                width=width, height=height, validity="boundary", relation=None,
                capture_eligible=True, source=source["url"], revision=source["revision"],
                license=source["license"], commands=scope.commands(page),
                purpose=source["purpose"], notes=source["notes"],
                derived_from=dict(file=source["file"], sha256=source["sha256"],
                                  change="; ".join(changes)),
            ))
    manifest = dict(schema=1, suite="public-zpl-20261002", sources_sha256=sha((HERE / "sources.json").read_bytes()), cases=cases)
    files["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, data in artifacts().items():
        path = HERE / name
        if args.check:
            assert path.read_bytes() == data, f"Stale public fixture: {name}"
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print("Public source hashes and derived fixtures verified" if args.check else "Public fixtures prepared")


if __name__ == "__main__":
    main()
