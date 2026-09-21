#!/usr/bin/env python3
"""Offline verification of shipping controls, state leaks, and final audit hashes."""

import hashlib
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
CONTROL = HERE / "legacy-controls"


def control_images(directory, manifest_name="manifest.json"):
    manifest = json.loads((directory / manifest_name).read_text())
    images = {}
    for row in manifest["cases"]:
        for suffix in ("zpl", "png"):
            data = (directory / (row["name"] + "." + suffix)).read_bytes()
            assert hashlib.sha256(data).hexdigest() == row[suffix + "_sha256"]
        source = (directory / (row["name"] + ".zpl")).read_bytes()
        canvas = f"^PW{row['width']}^LL{row['height']}".encode()
        reset = manifest["preview_reset_zpl"].encode()
        submitted = source[:3] + canvas + reset[3:-3] + source[3:]
        assert hashlib.sha256(submitted).hexdigest() == row["submitted_sha256"]
        with Image.open(directory / (row["name"] + ".png")) as image:
            images[row["name"]] = image.convert("RGB")
    return images


def main():
    images = control_images(CONTROL)
    original = images["shipping-original"]
    for name in (
        "shipping-clean",
        "shipping-units-reset",
        "shipping-after-dirty",
        "repeat-end",
    ):
        assert images[name].size == original.size
        assert images[name].tobytes() == original.tobytes(), name
    native = images["shipping-native-width"]
    assert (
        original.crop((10, 0, 832, 1218)).tobytes()
        == native.crop((0, 0, 822, 1218)).tobytes()
    )
    assert original.crop((0, 0, 10, 1218)).getextrema() == ((255, 255),) * 3
    assert native.crop((822, 0, 832, 1218)).getextrema() == ((255, 255),) * 3

    # This region excludes text and the y=250 separator; measure the QR top.
    def qr_top(image):
        ink = image.convert("L").point(lambda p: 255 if p < 128 else 0)
        return ink.crop((600, 0, 800, 240)).getbbox()[1]

    assert qr_top(original) == 149
    assert qr_top(images["shipping-qr-height-one"]) == 50
    repo = HERE.parents[1]
    roots = {
        "conformance": repo / "benchmarks/accuracy/conformance-reference",
        "arguments": repo / "benchmarks/accuracy/reference",
        "layout": repo / "benchmarks/accuracy/layout-reference",
        "external": repo / "benchmarks/accuracy/external-reference",
        "barcodes": repo / "references/barcodes-zd621-v1",
    }
    for suite, root in roots.items():
        report = json.loads((HERE / (suite + ".json")).read_text())
        assert not report["not_recaptured"]
        assert report["changed"] == (11 if suite == "conformance" else 0)
        for row in report["cases"]:
            name = row["name"]
            assert (
                hashlib.sha256((root / (name + ".zpl")).read_bytes()).hexdigest()
                == row["zpl_sha256"]
            )
            assert (
                hashlib.sha256((root / (name + ".png")).read_bytes()).hexdigest()
                == row["recaptured_png_sha256"]
            )
            if not row["pixels_equal"]:
                old_path = HERE / "superseded-qr" / (name + ".png")
                assert (
                    hashlib.sha256(old_path.read_bytes()).hexdigest()
                    == row["previous_png_sha256"]
                )
                old = Image.open(old_path).convert("RGB")
                new = Image.open(root / (name + ".png")).convert("RGB")
                w, h = old.size
                assert (
                    old.crop((0, 90, w, h)).tobytes()
                    == new.crop((0, 0, w, h - 90)).tobytes()
                )
        # Preserve and verify the observed caption contamination from the
        # intermediate height-only reset; these were never adopted as references.
        intermediate = json.loads(
            (HERE / ("height-only-" + suite + ".json")).read_text()
        )
        for row in intermediate["cases"]:
            if row["pixels_equal"] or row["name"].startswith("probe-qr-"):
                continue
            path = HERE / "height-only-captures" / (suite + "--" + row["name"] + ".png")
            assert (
                hashlib.sha256(path.read_bytes()).hexdigest()
                == row["recaptured_png_sha256"]
            )
            assert (
                hashlib.sha256((root / (row["name"] + ".png")).read_bytes()).hexdigest()
                == row["previous_png_sha256"]
            )

    for name, image in control_images(HERE / "remap-controls").items():
        reference = "readable-BC-N" if name == "repeat-end" else name
        expected = Image.open(roots["conformance"] / (reference + ".png")).convert(
            "RGB"
        )
        assert image.size == expected.size and image.tobytes() == expected.tobytes()
    for name, image in control_images(
        HERE / "legacy-defaults", "observations.json"
    ).items():
        ink = image.convert("L").point(lambda p: 255 if p < 128 else 0).getbbox()
        assert ink[3] - ink[1] == 100, name
        expected = Image.open(roots["conformance"] / (name + ".png")).convert("L")
        ink = expected.point(lambda p: 255 if p < 128 else 0).getbbox()
        assert ink[3] - ink[1] == 10, name
    repeat = json.loads((HERE / "qr-reverse-repeat.json").read_text())
    for row in repeat["cases"]:
        name = (
            repeat["cases"][0]["name"] if row["name"] == "repeat-end" else row["name"]
        )
        assert (
            hashlib.sha256(
                (roots["conformance"] / (name + ".png")).read_bytes()
            ).hexdigest()
            == row["png_sha256"]
        )
    print(
        "Verified shipping controls, legacy-state leaks, all final audit hashes, and eleven repeated QR corrections"
    )


if __name__ == "__main__":
    main()
