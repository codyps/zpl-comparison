"""Publish every renderer's public-label observations against native captures."""
import json
from pathlib import Path
import sys

from benchmarks import campaigns
from benchmarks import public_examples as public
from benchmarks.accuracy.pixels import sha


def main():
    _, _, reference, _ = public.verified_inputs()
    captured = {c["name"]: c for c in reference["cases"]}
    definitions = [dict(c, source="test-data/public-zpl/" + c["file"],
                        reference="references/public-zd621-20261002/" + c["name"] + ".png",
                        reference_sha256=captured[c["name"]]["png_sha256"])
                   for c in json.loads((public.CORPUS / "manifest.json").read_text())["cases"]]
    output = Path("docs/public-examples")
    data = campaigns.assemble("public-zpl", definitions, sys.argv[1:], "_public_rows", output,
                              printer={k: reference[k] for k in ["device", "firmware", "dpi", "method"]},
                              manifests={str(p.relative_to(Path.cwd())): sha(p) for p in [public.CORPUS / "manifest.json", public.REFERENCE / "manifest.json"]})
    campaigns.write(data, output)


if __name__ == "__main__":
    main()
