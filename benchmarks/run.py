#!/usr/bin/env python3
"""Serial, bounded multi-process benchmark. No printer or rendering service calls."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import signal
import statistics
import subprocess
import tempfile
import time
from PIL import Image
import PIL

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
MODES = {
    "local": ["parse", "png"],
    "toolchain": ["parse"],
    "forge": ["parse", "png"],
    "labelize": ["parse", "png"],
    "ffi": ["png"],
    "go": ["parse", "png"],
    "binarykits": ["parse", "png"],
    "zplr": ["parse", "png"],
    "builder": ["generate"],
    "python": ["generate"],
    "jszpl": ["generate"],
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(files):
    """Portable identities: avoid persisting machine-specific absolute paths."""
    rows = []
    for p in sorted(set(files)):
        try:
            name = str(p.relative_to(REPO))
        except ValueError:
            # Registry and installed runtime modules are outside the checkout.
            parts = p.parts
            offset = next(
                (i for i, s in enumerate(parts) if s.startswith("index.crates.io-")),
                None,
            )
            name = (
                "/".join(parts[offset + 1 :])
                if offset is not None
                else "/".join(parts[-3:])
            )
        rows.append({"path": name, "bytes": p.stat().st_size, "sha256": digest(p)})
    return rows


def node_files(name):
    base = ROOT / "adapters/node"
    lock = json.loads((base / "package-lock.json").read_text())["packages"]
    seen = set()

    def visit(key):
        if key in seen or not (base / key).is_dir():
            return
        seen.add(key)
        package = lock[key]
        deps = {
            **package.get("dependencies", {}),
            **package.get("optionalDependencies", {}),
            **package.get("peerDependencies", {}),
        }
        for dep in deps:
            parent = key
            while True:
                candidate = (
                    f"{parent}/node_modules/{dep}" if parent else f"node_modules/{dep}"
                )
                if candidate in lock:
                    visit(candidate)
                    break
                if not parent:
                    break
                parent = (
                    parent.rsplit("/node_modules/", 1)[0]
                    if "/node_modules/" in parent
                    else ""
                )

    visit(f"node_modules/{name}")
    return [p for key in seen for p in (base / key).rglob("*") if p.is_file()] + [
        base / "main.mjs"
    ]


def measure(command, env, timeout=90):
    """wait4 gives *this child* peak RSS, never the parent's cumulative maximum."""
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        start = time.monotonic()
        proc = subprocess.Popen(
            command, stdout=out, stderr=err, env=env, start_new_session=True
        )
        while True:
            pid, status, usage = os.wait4(proc.pid, os.WNOHANG)
            if pid:
                break
            if time.monotonic() - start > timeout:
                os.killpg(proc.pid, signal.SIGKILL)
                os.wait4(proc.pid, 0)
                proc.returncode = -9
                raise RuntimeError(f"Timed out after {timeout}s")
            time.sleep(0.005)
        proc.returncode = os.waitstatus_to_exitcode(status)
        out.seek(0)
        err.seek(0)
        stdout, stderr = out.read().decode(), err.read().decode(errors="replace")
        if proc.returncode:
            raise RuntimeError(f"Exit {proc.returncode}: {stderr[-3000:]}")
        value = json.loads(stdout.strip().splitlines()[-1])
        if value["ns"] <= 0 or value["checksum"] <= 0:
            raise RuntimeError("Invalid timing/output")
        value["peak_rss_bytes"] = usage.ru_maxrss * (
            1 if platform.system() == "Darwin" else 1024
        )
        value["process_seconds"] = time.monotonic() - start
        value["stderr"] = stderr[-3000:]
        return value


def check_output(path, mode, fixture):
    if mode == "png":
        with Image.open(path) as raw:
            raw.load()
            if raw.format != "PNG" or raw.size != (400, 300):
                raise RuntimeError(f"Unexpected image: {raw.format} {raw.size}")
            image = Image.new("RGBA", raw.size, "white")
            image.alpha_composite(raw.convert("RGBA"))
            pixels = list(image.convert("L").getdata())
        black = [v < 128 for v in pixels]
        if not any(black) or all(black):
            raise RuntimeError("Blank/solid image")
        result = {
            "width": 400,
            "height": 300,
            "black_pixels": sum(black),
            "sha256": digest(path),
        }
        if fixture == "boxes":
            # Zebra ^GB, bundled Programming Guide pp. 210-211: inward border.
            expected = [
                (
                    20 <= x < 120
                    and 20 <= y < 80
                    and not (24 <= x < 116 and 24 <= y < 76)
                )
                or (180 <= x < 260 and 100 <= y < 180)
                for y in range(300)
                for x in range(400)
            ]
            result["box_pixel_mismatches"] = sum(
                a != b for a, b in zip(black, expected)
            )
        return result
    if mode == "generate":
        source = path.read_text()
        n = int(fixture.split("-")[1])
        if not source.startswith("^XA") or not source.rstrip().endswith("^XZ"):
            raise RuntimeError("Label framing")
        if source.count("^FD") != n:
            raise RuntimeError("Wrong field count")
        for i in range(n):
            if f"Item {i:02}" not in source:
                raise RuntimeError("Missing field text")
        return {"fields": n, "bytes": path.stat().st_size, "sha256": digest(path)}
    if not path.stat().st_size:
        raise RuntimeError("Empty parse output")
    return {"check": "API completed; ASTs/framing are not semantically equivalent"}


def source_sizes(metadata):
    packages = {
        p["name"]: Path(p["manifest_path"]).parent for p in metadata["packages"]
    }
    paths = {
        "local": [packages["zpl"] / "src", packages["raster-diff"] / "src"],
        "toolchain": [
            packages[n] / "src"
            for n in [
                "zpl_toolchain_core",
                "zpl_toolchain_diagnostics",
                "zpl_toolchain_spec_tables",
                "zpl_toolchain_profile",
            ]
        ],
        "forge": [packages["zpl-forge"] / "src"],
        "labelize": [packages["labelize"] / "src"],
        "builder": [packages["zpl-builder"] / "src"],
        "ffi": [packages["zpl-rs"] / "src", ROOT / "_work/go-zpl"],
        "go": [ROOT / "_work/go-zpl"],
        "binarykits": [
            ROOT / "_work/BinaryKits.Zpl/src/BinaryKits.Zpl.Viewer",
            ROOT / "_work/BinaryKits.Zpl/src/BinaryKits.Zpl.Label",
        ],
        "python": [ROOT / "_work/python-zpl/zpl"],
        "jszpl": [ROOT / "_work/jszpl/src"],
        "zplr": [ROOT / "_work/zplr/src"],
    }
    result = {}
    for name, roots in paths.items():
        files = set()
        for root in roots:
            for p in root.rglob("*"):
                parts = p.relative_to(root).parts
                if any(
                    s
                    in {
                        "node_modules",
                        "target",
                        "bin",
                        "obj",
                        ".git",
                        "cmd",
                        "rust",
                        "site",
                        "tools",
                        "e2e",
                        "examples",
                        "__pycache__",
                    }
                    for s in parts
                ):
                    continue
                if p.suffix not in {".rs", ".go", ".cs", ".ts", ".py"} or any(
                    t in p.name for t in ["_test.", ".test.", ".spec."]
                ):
                    continue
                files.add(p)
        result[name] = {
            "bytes": sum(p.stat().st_size for p in files),
            "lines": sum(len(p.read_bytes().splitlines()) for p in files),
            "files": len(files),
            "source_manifest": manifest(files),
        }
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=REPO / "docs/benchmarks")
    ap.add_argument("--samples", type=int, default=5)
    ap.add_argument("--seconds", type=float, default=0.2)
    ap.add_argument("--only")
    ap.add_argument(
        "--iterations",
        type=int,
        help="Use this fixed batch size instead of calibration",
    )
    args = ap.parse_args()
    if args.samples < 1 or args.seconds <= 0:
        ap.error("samples and seconds must be positive")
    if args.iterations is not None and args.iterations < 1:
        ap.error("iterations must be positive")
    config = json.loads((ROOT / "_work/config.json").read_text())
    commands = config["commands"]
    if args.only:
        commands = {n: commands[n] for n in args.only.split(",")}
    env = {**os.environ, **config["environment"]}
    args.output.mkdir(parents=True, exist_ok=True)
    samples_dir = args.output / "samples"
    samples_dir.mkdir(exist_ok=True)
    jobs = []
    for name in commands:
        for mode in MODES[name]:
            for file in sorted(
                (ROOT / "fixtures").glob("*.txt" if mode == "generate" else "*.zpl")
            ):
                jobs.append((name, mode, file))
    random.Random(20260918).shuffle(jobs)
    results = []
    for name, mode, file in jobs:
        print(name, mode, file.stem, flush=True)
        ext = "png" if mode == "png" else "txt"
        artifact_dir = ROOT / "_work" if mode == "parse" else samples_dir
        artifact = artifact_dir / f"{name}-{mode}-{file.stem}.{ext}"
        artifact.unlink(missing_ok=True)
        row = {
            "library": name,
            "mode": mode,
            "fixture": file.stem,
            "input_sha256": digest(file),
            "input_bytes": file.stat().st_size,
            "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        command = commands[name] + [mode, str(file)]
        try:
            calibration = measure(command + ["1", str(artifact)], env)
            row["output_check"] = check_output(artifact, mode, file.stem)
            n = args.iterations or max(
                1, min(1000000, round(args.seconds * 1e9 / calibration["ns"]))
            )
            row["samples"] = [
                measure(command + [str(n), str(artifact)], env)
                for _ in range(args.samples)
            ]
            row["output_check"] = check_output(artifact, mode, file.stem)
            times = [s["ns"] / s["iterations"] for s in row["samples"]]
            row.update(
                status="ok",
                median_ns=statistics.median(times),
                min_ns=min(times),
                max_ns=max(times),
                peak_rss_bytes=max(s["peak_rss_bytes"] for s in row["samples"]),
            )
        except Exception as e:
            row.update(status="failed", error=str(e))
            print("FAILED:", e, flush=True)
        results.append(row)

    def version(cmd):
        try:
            return subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, text=True, env=env
            ).strip()
        except Exception as e:
            return str(e)

    metadata = json.loads((ROOT / "_work/cargo-metadata.json").read_text())
    sizes = source_sizes(metadata)
    for name, cmd in commands.items():
        if name in ["local", "toolchain", "labelize", "forge", "builder", "ffi", "go"]:
            files = [Path(cmd[0])]
            if name == "ffi":
                files.append(
                    Path(cmd[0]).parent
                    / ("libzpl.dylib" if platform.system() == "Darwin" else "libzpl.so")
                )
        elif name == "binarykits":
            files = [p for p in (ROOT / "_work/dotnet-out").rglob("*") if p.is_file()]
        elif name in ["zplr", "jszpl"]:
            files = node_files(name)
        else:
            files = list((ROOT / "_work/python-zpl/zpl").rglob("*.py")) + [
                ROOT / "adapters/python.py"
            ]
            pillow = Path(PIL.__file__).parent
            files += [
                p
                for root in [pillow, pillow.parent / "pillow.libs"]
                for p in root.rglob("*")
                if p.is_file() and "__pycache__" not in p.parts
            ]
        sizes[name]["artifact_bytes"] = sum(p.stat().st_size for p in set(files))
        sizes[name]["artifact_manifest"] = manifest(files)
    data = {
        "schema": 1,
        "host": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu": version(["sysctl", "-n", "machdep.cpu.brand_string"])
            if platform.system() == "Darwin"
            else version(["lscpu"]),
            "logical_cpus": os.cpu_count(),
            "rust": version(["rustc", "--version"]),
            "go": version(["go", "version"]),
            "node": version(["node", "--version"]),
            "python": platform.python_version(),
            "dotnet": version(
                [config["commands"].get("binarykits", ["dotnet"])[0], "--version"]
            ),
        },
        "git_revision": version(["git", "-C", str(REPO), "rev-parse", "HEAD"]),
        "git_dirty": bool(version(["git", "-C", str(REPO), "status", "--porcelain"])),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "samples": args.samples,
        "target_seconds": args.seconds,
        "seed": 20260918,
        "sizes": sizes,
        "results": results,
        "sources": json.loads((ROOT / "sources.lock.json").read_text()),
        "locks": {
            str(p.relative_to(ROOT)): digest(p)
            for p in [
                ROOT / "adapters/rust/Cargo.lock",
                ROOT / "adapters/node/package-lock.json",
                ROOT / "adapters/go/go.sum",
                ROOT / "adapters/dotnet/packages.lock.json",
            ]
            if p.exists()
        },
    }
    (args.output / "results.json").write_text(json.dumps(data, indent=2) + "\n")
    # Failures stay visible in the report; caller can inspect status without lost data.
    subprocess.run(
        [os.sys.executable, str(ROOT / "report.py"), str(args.output)], check=True
    )


if __name__ == "__main__":
    main()
