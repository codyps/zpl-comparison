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
            if spec.get("strict_native_canvas") and sha(Path(spec["image"]) / "image.png") != row["render_sha256"]:
                raise ValueError("Candidate render hash mismatch")
            actual = gray(Path(spec["image"]) / "image.png")
            if spec.get("strict_native_canvas") and actual.shape != ref.shape:
                row.update(dimensions_match=False, exact=False,
                           output_dimensions=[actual.shape[1], actual.shape[0]],
                           reference_dimensions=[ref.shape[1], ref.shape[0]],
                           comparison_status="canvas_mismatch",
                           comparison_diagnostic="Native dimensions differ; no padding, crop, alignment or score applied")
                Path(metadata).write_text(json.dumps(row, sort_keys=True) + "\n")
                return
            metrics, diff = compare(ref, actual)
            row.update(
                metrics, score=metrics["iou"] if metrics["reference_ink"] else None
            )
            if spec["suite"] in {"public", "paired"}:
                row["comparison"] = metrics
            save_difference(diff, output / "image.png")
        else:
            row["score"] = 0.0 if row["reference_ink"] and not spec.get("strict_native_canvas") and row["status"] != "not_captured" else None
    if spec["suite"] == "accuracy" and row["status"] not in ["rendered", "blank", "not_captured"]:
        row["execution_status"] = row["status"]
        row.update(
            status="error",
            error=row.get("diagnostic") or row.get("error") or row["execution_status"],
        )
    Path(metadata).write_text(json.dumps(row, sort_keys=True) + "\n")


if __name__ == "__main__":
    comparison(json.loads(Path(sys.argv[1]).read_text()), *sys.argv[2:])
