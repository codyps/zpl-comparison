"""Every renderer on each paired printer's exact submitted source and native canvas."""
import json
from pathlib import Path
import sys

from benchmarks import campaigns
from benchmarks.accuracy.metrics import compare
from benchmarks.accuracy.pixels import gray, sha


def main():
    root = Path("references/zq610-plus-v1")
    manifest = json.loads((root / "manifest.json").read_text())
    cases, common, unavailable = [], {}, {}
    for name, captured in manifest["cases"].items():
        if any(captured["status"].get(p, {}).get("status") != "captured" for p in ["zq610", "zd621"]):
            unavailable[name] = captured["status"]
            continue
        a, b = [gray(root / name / (p + ".png")) for p in ["zq610", "zd621"]]
        height, width = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
        metrics, _ = compare(a[:height, :width], b[:height, :width])
        common[name] = dict(region=[0, 0, width, height], **metrics)
        for printer in ["zq610", "zd621"]:
            status = captured["status"][printer]
            width, height = status["measurement"]["dimensions"]
            cases.append(dict(name=name + "-" + printer, paired_case=name, printer=printer,
                              source=str(root / name / (printer + ".zpl")),
                              reference=str(root / name / (printer + ".png")),
                              sha256=status["submitted_sha256"], reference_sha256=manifest["files"][name + "/" + printer + ".png"],
                              width=width, height=height, group="paired-printer",
                              notes="Full native canvas. Cross-printer common-region metrics are recorded separately.", capture=captured))
    output = Path("docs/benchmarks/zq610-plus")
    data = campaigns.assemble("paired", cases, sys.argv[1:], "_paired_rows", output,
                              manifests={str(root / "manifest.json"): sha(root / "manifest.json")},
                              common_coordinate_regions=common, unavailable=unavailable, printers=manifest["printers"])
    campaigns.write(data, output)


if __name__ == "__main__":
    main()
