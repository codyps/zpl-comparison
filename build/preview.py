"""A shared per-case viewport and independently cached image thumbnails."""

import json
import sys
from pathlib import Path

from benchmarks.accuracy.presentation import preview, viewport


def main(spec, destination):
    output = Path(destination)
    if spec["mode"] == "frame":
        paths = []
        for directory in spec["images"]:
            p = Path(directory)
            p = p / "image.png" if p.is_dir() else p
            if p.exists():
                paths.append(p)
        output.write_text(json.dumps(viewport(paths) if paths else [64, 64]) + "\n")
    else:
        output.mkdir(parents=True, exist_ok=True)
        p = Path(spec["image"])
        p = p / "image.png" if p.is_dir() else p
        if p.exists():
            preview(
                p,
                output / "image.png",
                tuple(json.loads(Path(spec["frame"]).read_text())),
                output / "unused.md",
                "",
            )


if __name__ == "__main__":
    main(json.loads(Path(sys.argv[1]).read_text()), sys.argv[2])
