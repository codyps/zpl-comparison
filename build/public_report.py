"""Publish current public-label observations against unchanged external captures."""

import json
from pathlib import Path
import platform

from benchmarks import public_examples as public
from benchmarks.accuracy.pixels import sha


def main():
    _, cases, reference, images = public.verified_inputs()
    output = public.OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    (output / "images").mkdir(exist_ok=True)
    rows = []
    for case in cases:
        row = json.loads((Path("_public_rows") / (case["name"] + ".json")).read_text())
        # The strict comparison action records the native metrics separately.
        if row["status"] in {"rendered", "blank"}:
            row["png_sha256"] = row["render_sha256"]
            if "comparison" in row:
                row["diff_sha256"] = sha(output / "images" / (case["name"] + "-diff.png"))
        rows.append(row)
    source = json.loads(Path("benchmarks/sources.lock.json").read_text())["zpl"]
    result = dict(schema=1, suite="public-zpl-20261002", results=rows,
                  measured_utc=max((r["observed_utc"] for r in rows if r.get("observed_utc", "")[:4].isdigit()), default="unavailable"),
                  host=platform.platform() if any("evidence_mode" not in r for r in rows) else "Saved trusted observations",
                  manifest_sha256=sha(public.CORPUS / "manifest.json"), reference_manifest_sha256=sha(public.REFERENCE / "manifest.json"),
                  renderer=dict(revision=source["rev"], profile="ZD621_203_DPI", dpi=203),
                  printer={k: reference[k] for k in ["device", "firmware", "dpi", "method"]})
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    public.verify(result, output, cases, images)
    service = public.service_comparisons(output, cases, images)
    artifacts = public.reports(result, service, output, cases)
    artifacts["labelary-results.json"] = json.dumps(service, indent=2) + "\n"
    for name, content in artifacts.items():
        (output / name).write_text(content)


if __name__ == "__main__":
    main()
