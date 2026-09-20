"""One independently cached metamorphic relation for one library."""

import json
import sys
from pathlib import Path

import numpy as np

from benchmarks.accuracy.pixels import gray


def main(spec, destination):
    rows = [json.loads(Path(p).read_text()) for p in spec["rows"]]
    status = "inconclusive"
    if len(rows) >= 2 and all(r["status"] == "rendered" for r in rows):
        images = [gray(Path(p) / "image.png") < 128 for p in spec["images"]]
        status = (
            "equal"
            if all(np.array_equal(images[0], p) for p in images[1:])
            else "different"
        )
    Path(destination).write_text(
        json.dumps(
            {
                "library": spec["library"],
                "set": spec["set"],
                "cases": [r["case"] for r in rows],
                "status": status,
            }
        )
        + "\n"
    )


if __name__ == "__main__":
    main(json.loads(Path(sys.argv[1]).read_text()), sys.argv[2])
