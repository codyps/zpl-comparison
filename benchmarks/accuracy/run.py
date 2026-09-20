#!/usr/bin/env python3
"""Offline differential accuracy against hash-verified printer raster captures."""

import argparse
import json
import os
import platform
import shutil
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
LIBRARIES = [
    "codyps-zpl",
    "labelize",
    "forge",
    "go",
    "ffi",
    "binarykits",
    "zplr",
    "labelary",
]


sys.path.insert(0, str(ROOT))
from accuracy.pixels import gray, sha
from accuracy.metrics import compare


def corpus(fresh=ROOT / "accuracy/reference"):
    cases = []
    manifest = json.loads((fresh / "manifest.json").read_text())
    if manifest["status"] != "complete" or not manifest["repeat_pixels_equal"]:
        raise ValueError("Unstable/incomplete reference capture")
    for row in manifest["cases"]:
        if (
            sha(fresh / (row["name"] + ".zpl")) != row["zpl_sha256"]
            or sha(fresh / (row["name"] + ".png")) != row["png_sha256"]
        ):
            raise ValueError("Capture hash mismatch")
        if row["group"] == "repeatability":
            continue
        cases.append(
            {
                **row,
                "id": "argument-" + row["name"],
                "source": "fresh arguments",
                "zpl": fresh / (row["name"] + ".zpl"),
                "reference": fresh / (row["name"] + ".png"),
            }
        )
    if not np.array_equal(
        gray(fresh / (manifest["cases"][0]["name"] + ".png")),
        gray(fresh / "repeat-end.png"),
    ):
        raise ValueError("Repeated control changed")
    old = REPO / "references/barcodes-zd621-v1"
    historical = json.loads((old / "manifest.json").read_text())
    for name, row in historical["cases"].items():
        zpl = old / (name + ".zpl")
        import re

        commands = re.findall(r"\^(B[0-9A-Z])", zpl.read_text())
        cases.append(
            dict(
                id="barcode-" + name,
                name=name,
                group="barcode-formats",
                command="^" + next((c for c in commands if c != "BY"), "?"),
                arguments="See exact archived ZPL",
                width=historical["width"],
                height=1218,
                source="archived barcode development corpus",
                zpl=zpl,
                reference=old / (name + ".png"),
                zpl_sha256=row["zpl_sha256"],
                png_sha256=row["printer_png_sha256"],
            )
        )
    for row in cases:
        if (
            sha(row["zpl"]) != row["zpl_sha256"]
            or sha(row["reference"]) != row["png_sha256"]
        ):
            raise ValueError(f"Capture hash mismatch: {row['id']}")
    return cases, manifest, historical


def preflight(cfg, libraries):
    """Reject missing harness dependencies before overwriting saved evidence."""
    env = {**os.environ, **cfg.get("environment", {})}
    for name in libraries:
        command = cfg["commands"][name]
        if not shutil.which(command[0], path=env.get("PATH")):
            raise ValueError(
                f"Missing adapter executable for {name}: {command[0]}; run prepare.py"
            )
        for arg in command[1:]:
            if Path(arg).is_absolute() and not Path(arg).is_file():
                raise ValueError(f"Missing adapter dependency for {name}: {arg}")
        if name == "ffi":
            native = Path(command[0]).parent / (
                "libzpl.dylib" if sys.platform == "darwin" else "libzpl.so"
            )
            if not native.is_file():
                raise ValueError(
                    f"Missing FFI native library: {native}; run prepare.py"
                )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", type=Path, default=ROOT / "accuracy/reference")
    ap.add_argument("--output", type=Path, default=REPO / "docs/benchmarks/accuracy")
    args = ap.parse_args()
    cfg = json.loads((ROOT / "_work/config.json").read_text())
    sys.path.insert(0, str(ROOT))
    from labelary import DEFAULT, register, validate

    register(cfg)
    validate(DEFAULT)
    missing = set(LIBRARIES) - cfg["commands"].keys()
    if missing:
        ap.error(f"Build all rendering adapters first; missing: {sorted(missing)}")
    env = {**os.environ, **cfg["environment"]}
    preflight(cfg, LIBRARIES)
    identities = {}
    for name in LIBRARIES:
        command = cfg["commands"][name]
        paths = [Path(v) for v in command if Path(v).is_file()]
        if name == "ffi":
            paths.append(
                Path(command[0]).parent
                / ("libzpl.dylib" if sys.platform == "darwin" else "libzpl.so")
            )
        if name == "zplr":
            paths.extend(
                [ROOT / "adapters/node/package-lock.json", ROOT / "sources.lock.json"]
            )
        if name == "binarykits":
            paths.extend((ROOT / "_work/dotnet-out").glob("*.dll"))
        if name == "labelary":
            paths.extend(
                [ROOT / "labelary.py", REPO / "docs/benchmarks/labelary/captures.json"]
            )
        identities[name] = [{"name": p.name, "sha256": sha(p)} for p in paths]
    cases, fresh, old = corpus(args.reference.resolve())
    dest = args.output
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "images").mkdir(exist_ok=True)
    work = ROOT / "_work/accuracy"
    work.mkdir(exist_ok=True)
    rows = []
    refs = {r["id"]: gray(r["reference"]) for r in cases}
    for ci, case in enumerate(cases):
        ref = refs[case["id"]]
        reference_ink = int(np.count_nonzero(ref < 128))
        for name in LIBRARIES:
            key = case["id"] + "-" + name
            output = work / (key + ".png")
            output.unlink(missing_ok=True)
            for suffix in (".png", "-diff.png"):
                (dest / "images" / (key + suffix)).unlink(missing_ok=True)
            command = cfg["commands"][name] + [
                "accuracy",
                str(case["zpl"]),
                "1",
                str(output),
                str(case["width"]),
                str(case["height"]),
            ]
            row = dict(
                library=name,
                case=case["id"],
                group=case["group"],
                reference_ink=reference_ink,
                score=None if reference_ink == 0 else 0.0,
            )
            try:
                process = subprocess.run(
                    command,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=45,
                )
                if process.returncode:
                    raise RuntimeError(process.stderr.decode(errors="replace")[-1800:])
                actual = gray(output)
                metrics, diff = compare(ref, actual)
                row.update(
                    metrics,
                    status="rendered" if metrics["output_ink"] else "blank",
                    score=metrics["iou"] if reference_ink else None,
                    raw_png_sha256=sha(output),
                    stderr=process.stderr.decode(errors="replace")[-1800:],
                )
                # Lossless re-encoding keeps checked-in raster artifacts small; no registration or resizing.
                Image.fromarray(actual).save(
                    dest / "images" / (key + ".png"), optimize=True
                )
                Image.fromarray(diff).save(
                    dest / "images" / (key + "-diff.png"), optimize=True
                )
            except Exception as error:
                row.update(status="error", error=str(error))
            rows.append(row)
        print(f"{ci + 1}/{len(cases)} {case['id']}", flush=True)
    serial = []
    for case in cases:
        serial.append(
            {
                **case,
                "zpl": str(case["zpl"].relative_to(REPO)),
                "reference": str(case["reference"].relative_to(REPO)),
            }
        )
    result = dict(
        schema=1,
        host={
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        measured_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        threshold=128,
        cases=serial,
        results=rows,
        adapters=identities,
        fresh_reference={k: v for k, v in fresh.items() if k != "cases"},
        archived_reference={k: v for k, v in old.items() if k != "cases"},
    )
    (dest / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    subprocess.run(
        [sys.executable, str(ROOT / "accuracy/report.py"), str(dest)], check=True
    )


if __name__ == "__main__":
    main()
