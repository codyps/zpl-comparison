"""One independently cached printer/image comparison and difference PNG."""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from benchmarks.accuracy.metrics import compare
from benchmarks.accuracy.pixels import gray, sha


def save_difference(diff, path):
    """Lossless fixed-palette PNG, without expensive RGB compression searches."""
    indices = np.zeros(diff.shape[:2], dtype=np.uint8)
    indices[diff[:, :, 0] == 0] = 1
    indices[diff[:, :, 0] == 220] = 2
    indices[diff[:, :, 1] == 160] = 3
    image = Image.fromarray(indices).convert("P")
    image.putpalette([255, 255, 255, 0, 0, 0, 220, 0, 150, 0, 160, 220])
    image.save(path, bits=2, compress_level=1)


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
            save_difference(diff, output / "image.png")
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
