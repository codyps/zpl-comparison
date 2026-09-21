"""Assemble result documents without rendering or comparing any image."""

import json
import platform
import sys
from pathlib import Path

from benchmarks.accuracy.pixels import sha


def aggregate(spec, destination):
    output = Path(destination)
    output.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(Path(p).read_text()) for p in spec["rows"]]
    data = spec["metadata"]
    data["cases"] = spec["cases"]
    data["results"] = rows
    data["measured_utc"] = max(
        [r.get("observed_utc", spec["captured_utc"]) for r in rows]
    )
    data["generation"] = (
        "Bazel: independently cached local renders; saved printer and Labelary captures"
    )
    data["host"] = (
        {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        }
        if spec["suite"] == "accuracy"
        else platform.platform()
    )
    if spec["suite"] != "accuracy":
        data["manifest_sha256"] = sha(Path(spec["manifest"]))
        data["relations"] = [json.loads(Path(p).read_text()) for p in spec["relations"]]
    else:
        data["adapters"] = {
            name: json.loads(Path(path).joinpath("identity.json").read_text())
            for name, path in spec["libraries"].items()
        }
    if "saved_provenance" in spec:
        data.update(spec["saved_provenance"])
        data["generation"] = "Bazel: independently cached comparisons of saved renderer and printer evidence"
    target = output / spec["renders"] / "results.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(data, indent=2) + "\n")
    if spec["suite"] != "accuracy":
        compared = [json.loads(Path(p).read_text()) for p in spec["comparisons"]]
        for row in compared:
            prefix = row["case"] + "-" + row["library"]
            if row["status"] in ["rendered", "blank"]:
                row["image"] = spec["renders"] + "/images/" + prefix + ".png"
                if "iou" in row:
                    row["diff"] = spec["base"] + "/images/" + prefix + "-diff.png"
        features = {
            "schema": 1,
            "measured_utc": data["measured_utc"],
            "inputs": {
                spec["manifest_name"]: sha(Path(spec["manifest"])),
                spec["renders"] + "/results.json": sha(target),
                spec["reference_name"]: sha(Path(spec["reference_manifest"])),
            },
            "coverage": spec["coverage"],
            "results": compared,
        }
        features["coverage"].update(
            rendered_images=sum("image" in r for r in compared),
            difference_images=sum("diff" in r for r in compared),
        )
        target = output / spec["base"] / "results.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(features, indent=2) + "\n")


if __name__ == "__main__":
    aggregate(json.loads(Path(sys.argv[1]).read_text()), sys.argv[2])
