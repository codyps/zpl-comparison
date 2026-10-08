"""One source/canvas/library render. No comparison or reporting dependencies."""

import json
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image

from benchmarks.accuracy.pixels import gray, sha


def render(spec, metadata, images):
    output = Path(images).resolve()
    output.mkdir(parents=True, exist_ok=True)
    row = dict(spec["row"])
    row.update(source_sha256=spec["sha256"], requested_dimensions=[spec["width"], spec["height"]],
               render_profile=spec.get("render_profile", "zd621-203dpi"), timeout_seconds=spec.get("timeout", 45))
    if "input_identity" in spec:
        row["input_identity"] = spec["input_identity"]
    source = Path(spec["source"])
    font_metadata, font_preamble = None, b""
    if spec.get("font_bundle"):
        from build.font_profile import configure
        font_metadata, font_preamble = configure(spec["font_bundle"], row["library"])
        row["font_control"] = font_metadata
    if sha(source) != spec["sha256"]:
        raise ValueError("Input hash mismatch: " + str(source))
    image = output / "image.png"
    if "saved" in spec:
        if spec["saved"]:
            if sha(Path(spec["saved"])) != spec["png_sha256"]:
                raise ValueError("Saved service capture hash mismatch")
            row["raw_png_sha256"] = spec["png_sha256"]
            shutil.copyfile(spec["saved"], image)
    else:
        library = Path(spec["library"]).resolve()
        if (library / "identity.json").exists():
            row["adapter_identity_sha256"] = sha(library / "identity.json")
        command = json.loads((library / "command.json").read_text())
        command = [
            str(library / arg) if (library / arg).exists() else arg for arg in command
        ]
        row["observed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with tempfile.TemporaryDirectory(prefix="zpl-render-") as temporary:
            render_source = source.resolve()
            if font_preamble:
                render_source = Path(temporary) / "font-controlled.zpl"
                render_source.write_bytes(font_preamble + source.read_bytes())
                row["submitted_source_sha256"] = sha(render_source)
            env = {
                **os.environ,
                "HOME": temporary,
                # Never inherit a caller profile into unrelated suites.
                "ZPL_RENDER_PROFILE": spec.get("render_profile", "zd621-203dpi"),
                "ZPL_FONT_DIR": str(Path(spec["font_bundle"]).resolve()) if font_metadata and font_metadata["mode"] in {"supplied-callback", "supplied-bitmap-and-callback"} else "",
                "TMPDIR": temporary,
                "DOTNET_CLI_HOME": temporary,
                "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
                "DOTNET_ROOT": str(library / "runtime"),
                "DYLD_LIBRARY_PATH": str(library),
                "LD_LIBRARY_PATH": os.pathsep.join(filter(None, [str(library), os.environ.get("LD_LIBRARY_PATH", "")])),
            }
            try:
                proc = subprocess.run(
                    command
                    + [
                        "accuracy",
                        str(render_source),
                        "1",
                        str(image),
                        str(spec["width"]),
                        str(spec["height"]),
                    ],
                    cwd=temporary,
                    env=env,
                    capture_output=True,
                    stdin=subprocess.DEVNULL,
                    check=False,
                    timeout=spec.get("timeout", 45),
                )
                row.update(
                    returncode=proc.returncode,
                    diagnostic=proc.stderr.decode(errors="replace")[-1800:],
                )
                row["status"] = (
                    "crashed"
                    if proc.returncode < 0
                    else "error"
                    if proc.returncode
                    else "rendered"
                )
            except subprocess.TimeoutExpired:
                row.update(
                    status="timeout", diagnostic="Renderer exceeded its time limit"
                )
        if row["status"] in ["error", "crashed", "timeout"]:
            image.unlink(missing_ok=True)
        else:
            # A successful command without a readable PNG is a harness failure.
            row["raw_png_sha256"] = sha(image)
    if image.exists():
        raster = gray(image)
        # Encode once. Compression changes bytes, never scoring pixels.
        Image.fromarray(raster).save(image, compress_level=1)
        ink = int(np.count_nonzero(raster < 128))
        row.update(
            status="rendered" if ink else "blank",
            ink=ink,
            width=raster.shape[1],
            height=raster.shape[0],
            render_sha256=sha(image),
            pixel_sha256=hashlib.sha256(raster.tobytes()).hexdigest(),
        )
    elif row["status"] in ["rendered", "blank"]:
        raise ValueError("Missing successful render")
    Path(metadata).write_text(json.dumps(row, sort_keys=True) + "\n")


if __name__ == "__main__":
    render(json.loads(Path(sys.argv[1]).read_text()), *sys.argv[2:])
