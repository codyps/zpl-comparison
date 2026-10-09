"""Canonical lossless raster loading shared by capture and Bazel actions."""

import hashlib

import numpy as np
from PIL import Image


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gray(path):
    with Image.open(path) as image:
        if image.width * image.height > 16_000_000:
            raise ValueError("Raster limit exceeded")
        image.load()
        if image.mode in {"1", "L", "RGB"} and "transparency" not in image.info:
            return np.array(image.convert("L"))
        rgba = image.convert("RGBA")
        white = Image.new("RGBA", image.size, "white")
        white.alpha_composite(rgba)
        return np.array(white.convert("L"))
