"""Import one saved observation without running a renderer or rewriting its PNG."""

import json
import shutil
from pathlib import Path


def saved(spec, metadata, images):
    output = Path(images)
    output.mkdir(parents=True, exist_ok=True)
    row = spec["row"]
    if row["status"] in ("rendered", "blank"):
        # Missing successful evidence is a build failure, never a synthetic blank.
        shutil.copyfile(spec["image"], output / "image.png")
    elif spec.get("image"):
        raise ValueError("Failed observation must not carry a render")
    Path(metadata).write_text(json.dumps(row, sort_keys=True) + "\n")
