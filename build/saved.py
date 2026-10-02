"""Import one saved observation without running a renderer or rewriting its PNG."""

import json
import shutil
import hashlib
from pathlib import Path

COMPUTED = {"score", "reference_ink", "output_ink", "missing", "extra", "iou", "precision", "recall",
            "canvas_disagreement", "dimensions_match", "ink_exact", "exact", "output_dimensions",
            "reference_dimensions", "comparison", "comparison_status", "comparison_diagnostic",
            "image", "diff", "diff_sha256"}


def saved(spec, metadata, images):
    if "saved" in spec:
        from build.render import render
        return render(spec, metadata, images)
    output = Path(images)
    output.mkdir(parents=True, exist_ok=True)
    row = dict(spec["row"])
    if "expected" in spec:
        evidence = json.loads(Path(spec["evidence"]).read_text()) if spec.get("evidence") else None
        expected = spec["expected"]
        row.update(expected)
        mismatch = [key for key, value in expected.items() if not evidence or evidence.get(key) != value]
        if mismatch:
            row.update(status="not_captured", diagnostic="No compatible trusted observation: " + ", ".join(mismatch),
                       evidence_mode="unavailable", observed_utc="unavailable")
            if evidence:
                row["baseline_revision"] = evidence.get("baseline_revision")
                row["baseline_observed_utc"] = evidence.get("observed_utc")
        else:
            # Printer references and metric code can change without rerendering.
            # Only replay execution evidence; comparison actions recompute scores.
            row = {k: v for k, v in evidence.items() if k not in COMPUTED}
            row["status"] = row.pop("execution_status", row["status"])
            row.update(spec["row"], evidence_mode="saved")
    if row["status"] in ("rendered", "blank"):
        # Missing successful evidence is a build failure, never a synthetic blank.
        source = Path(spec["image"])
        if row.get("render_sha256") and hashlib.sha256(source.read_bytes()).hexdigest() != row["render_sha256"]:
            raise ValueError("Saved render hash mismatch")
        shutil.copyfile(source, output / "image.png")
    elif spec.get("image") and "expected" not in spec:
        raise ValueError("Failed observation must not carry a render")
    Path(metadata).write_text(json.dumps(row, sort_keys=True) + "\n")
