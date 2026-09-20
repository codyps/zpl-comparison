"""Compact linked previews; full-size images remain the only scoring inputs."""

import os
from PIL import Image, ImageChops

MAX_SIZE = (360, 160)


def rgb(path):
    with Image.open(path) as image:
        image.load()
        rgba = image.convert("RGBA")
        white = Image.new("RGBA", rgba.size, "white")
        white.alpha_composite(rgba)
        return white.convert("RGB")


def viewport(paths):
    width = height = bottom = 0
    for path in paths:
        image = rgb(path)
        width = max(width, image.width)
        height = max(height, image.height)
        bounds = ImageChops.difference(
            image, Image.new("RGB", image.size, "white")
        ).getbbox()
        if bounds:
            bottom = max(bottom, bounds[3])
    return width, min(height, max(64, bottom + 12))


def preview(source, target, frame, page, label, check=False):
    canvas = Image.new("RGB", frame, "white")
    canvas.paste(rgb(source), (0, 0))
    canvas.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
    if check:
        with Image.open(target) as saved:
            if (
                saved.size != canvas.size
                or saved.convert("RGB").tobytes() != canvas.tobytes()
            ):
                raise ValueError("Stale compact preview: " + str(target))
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(target)
    return f"[![{label}]({os.path.relpath(target, page.parent)})]({os.path.relpath(source, page.parent)})"


LEGEND = (
    "Black = matching ink; magenta = printer only; cyan = library only. "
    "Compact previews share a common origin and crop only trailing blank space; "
    "click for the full-resolution image. Scores always use uncropped original pixels."
)
