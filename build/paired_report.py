"""Current paired-printer profile results, with offline original capture replay."""

import json
from pathlib import Path

from benchmarks.accuracy.metrics import compare
from benchmarks.accuracy.pixels import gray, sha
from benchmarks.zq610_pages import generate


def directional(metrics):
    union = metrics["reference_ink"] + metrics["extra"]
    return dict(dimensions_equal=metrics["dimensions_match"], exact=metrics["exact"],
                underpaint=metrics["missing"], overpaint=metrics["extra"],
                both_black=metrics["reference_ink"] - metrics["missing"],
                foreground_iou=metrics["iou"] if union else None, nonblank=union > 0)


def main():
    root = Path("references/zq610-plus-v1")
    manifest = json.loads((root / "manifest.json").read_text())
    result = dict(manifest_sha256=sha(root / "manifest.json"), profile="zq610-plus-203dpi",
                  zd621_profile="zd621-preview-203dpi", cases={}, unavailable={})
    for name, captured in manifest["cases"].items():
        if any(captured["status"].get(p, {}).get("status") != "captured" for p in ["zq610", "zd621"]):
            result["unavailable"][name] = captured["status"]
            continue
        entry = dict(capture=captured)
        for printer in ["zq610", "zd621"]:
            row = json.loads((Path("_paired_rows") / (name + "-" + printer + ".json")).read_text())
            if "comparison" in row:
                entry[printer] = directional(row["comparison"])
            else:
                entry[printer] = dict(exact=None if row["status"] == "not_captured" else False,
                                      dimensions_equal=False, error=row.get("diagnostic", row.get("comparison_status", row["status"])))
            entry[printer]["observation"] = row
            if row["status"] in {"rendered", "blank"}:
                local = root / name / (printer + "-local.png")
                entry[printer].update(local_png_sha256=sha(local), local_pixels_sha256=row["pixel_sha256"])
        a, b = [gray(root / name / (printer + ".png")) for printer in ["zq610", "zd621"]]
        height, width = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
        metrics, _ = compare(a[:height, :width], b[:height, :width])
        entry["common_coordinate_region"] = dict(region=[0, 0, width, height], **directional(metrics))
        result["cases"][name] = entry
    result["summary"] = {p: sum(bool(r[p].get("exact")) for r in result["cases"].values())
                         for p in ["zq610", "zd621", "common_coordinate_region"]}
    result["summary"].update(paired_cases=len(result["cases"]), unavailable_cases=len(result["unavailable"]))
    (root / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    generate(root, Path("docs/benchmarks/zq610-plus"))


if __name__ == "__main__":
    main()
