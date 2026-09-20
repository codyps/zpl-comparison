"""One independently cached printer/image comparison and difference PNG."""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from benchmarks.accuracy.metrics import compare
from benchmarks.accuracy.pixels import gray, sha


def comparison(spec, metadata, images):
    row = json.loads(Path(spec["row"]).read_text())
    output = Path(images)
    output.mkdir(parents=True, exist_ok=True)
    row["score"] = None
    if spec.get("reference"):
        reference = Path(spec["reference"])
        if sha(reference) != spec["sha256"]:
            raise ValueError("Printer reference hash mismatch")
        ref = gray(reference)
        row["reference_ink"] = int(np.count_nonzero(ref < 128))
        if row["status"] in ["rendered", "blank"]:
            metrics, diff = compare(ref, gray(Path(spec["image"]) / "image.png"))
            row.update(
                metrics, score=metrics["iou"] if metrics["reference_ink"] else None
            )
            Image.fromarray(diff).save(output / "image.png", optimize=True)
        else:
            row["score"] = 0.0 if row["reference_ink"] else None
    if spec["suite"] == "accuracy" and row["status"] not in ["rendered", "blank"]:
        row["execution_status"] = row["status"]
        row.update(
            status="error",
            error=row.get("diagnostic") or row.get("error") or row["execution_status"],
        )
    Path(metadata).write_text(json.dumps(row, sort_keys=True) + "\n")


if __name__ == "__main__":
    comparison(json.loads(Path(sys.argv[1]).read_text()), *sys.argv[2:])
