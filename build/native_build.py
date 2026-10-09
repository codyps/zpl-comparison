"""Build adapters offline, or assemble outputs supplied by language rules."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


def source_size(root, name, native=None):
    roots = {
        "codyps-zpl-node": [root / "benchmarks/_work/codyps-zpl-node" / p for p in ["zpl/src", "raster-diff/src", "zpl-bitmap-fonts/src", "zpl-wasm/src", "zpl-node"]],
        "codyps-zpl": [root / "benchmarks/_work/zpl/zpl/src", root / "benchmarks/_work/zpl/raster-diff/src"],
        "go": [root / "benchmarks/_work/go-zpl"],
        "go-native": [root / "benchmarks/_work/go-zpl"],
        "binarykits": [root / "benchmarks/_work/BinaryKits.Zpl/src/BinaryKits.Zpl.Viewer", root / "benchmarks/_work/BinaryKits.Zpl/src/BinaryKits.Zpl.Label"],
        "zplr": [root / "benchmarks/_work/zplr/src"],
        "zebrash": [root / "benchmarks/_work/zebrash"],
        "zpl-renderer-js": [root / "benchmarks/_work/zpl-renderer-js/src", root / "benchmarks/_work/zpl-renderer-js/zebrash"],
        "zebrash-ts": [root / "benchmarks/_work/zebrash-ts/packages/core/src", root / "benchmarks/_work/zebrash-ts/packages/node/src"],
    }
    package = {"labelize": "labelize", "forge": "zpl-forge", "ffi": "zpl-rs"}.get(name)
    if package:
        roots[name] = [p.parent / "src" for p in (root / "vendor").glob("*/Cargo.toml")
                       if tomllib.loads(p.read_text()).get("package", {}).get("name") == package]
    selected = roots.get(name, [])
    if not selected or any(not p.is_dir() for p in selected):
        raise ValueError("Missing implementation source for " + name)
    files = sorted({p for folder in selected for p in folder.rglob("*")
                    if p.is_file() and p.suffix in {".rs", ".go", ".cs", ".ts", ".js", ".cjs", ".mjs"}
                    and not any(part in {"cmd", "bin", "obj", "target", "node_modules", "examples", "tests", "pkg", ".git"} for part in p.relative_to(folder).parts)
                    and not any(mark in p.name for mark in ("_test.", ".test.", ".spec."))})
    if not files:
        raise ValueError("No implementation source files for " + name)
    result = dict(bytes=sum(p.stat().st_size for p in files),
                  lines=sum(len(p.read_bytes().splitlines()) for p in files), files=len(files),
                  source_manifest=[dict(name=str(p.relative_to(root)), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
    if name == "ffi":
        go = json.loads((native / "size.json").read_text())
        for field in ("bytes", "lines", "files"):
            result[field] += go[field]
        result["source_manifest"] += go["source_manifest"]
    return result


def build(spec, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Bazel's spawn runner may override TMPDIR. Permit disk-backed build scratch
    # space on hosts whose /tmp is a small tmpfs.
    with tempfile.TemporaryDirectory(prefix="zpl-build-", dir=os.environ.get("ZPL_BUILD_TMPDIR")) as temporary:
        root = Path(temporary)
        for source, relative in spec["inputs"]:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            target.chmod(Path(source).stat().st_mode)
        tools = Path(spec["tools"]).resolve()
        env = {
            **os.environ,
            "HOME": str(root / "home"),
            "TMPDIR": str(root),
            "PATH": os.pathsep.join(
                [str(tools / p / "bin") for p in ["rust", "go", "node"]]
                + [os.environ.get("PATH", "/usr/bin:/bin")]
            ),
            "CARGO_HOME": str(root / "cargo"),
            "CARGO_BUILD_JOBS": "2",
            "GOMAXPROCS": "2",
            "CARGO_TARGET_DIR": str(root / "target"),
            "GOCACHE": str(root / "go-cache"),
            "GOMODCACHE": str(root / "modules"),
            "GOPATH": str(root / "go-home"),
            "GOPROXY": "off",
            "GOSUMDB": "off",
            "GOTOOLCHAIN": "local",
            "SOURCE_DATE_EPOCH": "0",
        }

        def run(*args, cwd=root):
            subprocess.run(list(map(str, args)), cwd=cwd, env=env, check=True)

        name = spec["library"]
        if name in ["codyps-zpl", "labelize", "forge", "ffi"]:
            (root / "cargo").mkdir()
            (root / "cargo/config.toml").write_text(
                '[source.crates-io]\nreplace-with="vendored"\n[source.vendored]\ndirectory='
                + json.dumps(str(root / "vendor"))
                + "\n"
            )
            if name == "ffi":
                native = Path(spec["native"]).resolve()
                env.update(
                    LIBZPL_PATH=str(native / ("libzpl.dylib" if sys.platform == "darwin" else "libzpl.so")),
                    LIBZPL_COPY_TO=str(root / "target/release"),
                )
            env["DYLD_FALLBACK_LIBRARY_PATH"] = str(tools / "rust/lib")
            run(
                "cargo",
                "build",
                "--offline",
                "--locked",
                "--release",
                "--manifest-path",
                root / "benchmarks/adapters/rust/Cargo.toml",
                "--features",
                name,
                "--bin",
                name,
            )
            shutil.copy2(root / "target/release" / name, output / "adapter")
            if name == "ffi":
                for path in native.glob("libzpl.*"):
                    shutil.copy2(path, output / path.name)
        elif name in ["go", "go-native", "zebrash"]:
            if name == "go-native":
                filename = "libzpl.dylib" if sys.platform == "darwin" else "libzpl.so"
                run(
                    "go",
                    "build",
                    "-mod=readonly",
                    "-trimpath",
                    "-buildvcs=false",
                    "-buildmode=c-shared",
                    "-o",
                    output / filename,
                    "./cmd/libzpl",
                    cwd=root / "benchmarks/_work/go-zpl",
                )
            else:
                run(
                    "go",
                    "build",
                    "-mod=readonly",
                    "-trimpath",
                    "-buildvcs=false",
                    "-ldflags=-s -w",
                    "-o",
                    output / "adapter",
                    ".",
                    cwd=root / "benchmarks/adapters" / ("zebrash" if name == "zebrash" else "go"),
                )
        elif name == "codyps-zpl-node":
            (root / "cargo").mkdir()
            (root / "cargo/config.toml").write_text(
                '[source.crates-io]\nreplace-with="vendored"\n[source.vendored]\ndirectory='
                + json.dumps(str(root / "vendor")) + "\n")
            checkout = root / "benchmarks/_work/codyps-zpl-node"
            run("cargo", "build", "--offline", "--locked", "--release", "--target",
                "wasm32-unknown-unknown", "-p", "zpl-wasm", cwd=checkout)
            package = output / name
            package.mkdir()
            for filename in ["package.json", "index.cjs", "index.mjs", "index.d.ts"]:
                shutil.copy2(checkout / "zpl-node" / filename, package / filename)
            shutil.copy2(checkout / "LICENSE", package / "LICENSE")
            run(tools / "wasm-bindgen/wasm-bindgen",
                root / "target/wasm32-unknown-unknown/release/zpl_wasm.wasm",
                "--target", "nodejs", "--out-dir", package / "pkg", "--out-name", "zpl_wasm")
            (output / "node").mkdir()
            shutil.copy2(root / "benchmarks/adapters/node/renderers.mjs", output / "node/renderers.mjs")
            shutil.copytree(tools / "node", output / "runtime", symlinks=True)
        elif name == "zplr":
            shutil.copytree(root / "node_modules", output / "node_modules")
            shutil.copy2(
                root / "benchmarks/adapters/node/main.mjs", output / "main.mjs"
            )
            shutil.copytree(tools / "node", output / "runtime", symlinks=True)
        elif name in ["zpl-renderer-js", "zebrash-ts"]:
            # Keep independent npm closures so deployment sizes exclude other renderers.
            package = output / name
            package.mkdir()
            shutil.copytree(root / "node_modules", package / "node_modules")
            shutil.copy2(root / "package.json", package / "package.json")
            if name == "zebrash-ts":
                shutil.copy2(root / "benchmarks/adapters/zebrash-ts/api.mjs", package / "api.mjs")
            driver = output / "node"
            driver.mkdir()
            shutil.copy2(root / "benchmarks/adapters/node/renderers.mjs", driver / "renderers.mjs")
            shutil.copytree(tools / "node", output / "runtime", symlinks=True)
        elif name == "binarykits":
            shutil.copytree(root / "published", output, dirs_exist_ok=True)
            shutil.copytree(root / "benchmarks/adapters/dotnet/fonts", output / "fonts")
            icu_version = tools / "dotnet/icu-version.txt"
            if icu_version.exists():
                config_path = output / "Comparison.runtimeconfig.json"
                config = json.loads(config_path.read_text())
                config["runtimeOptions"].setdefault("configProperties", {})["System.Globalization.AppLocalIcu"] = icu_version.read_text().strip()
                config_path.unlink()  # Published Bazel inputs are read-only.
                config_path.write_text(json.dumps(config, indent=2) + "\n")
            shutil.copytree(tools / "dotnet/host", output / "runtime/host")
            shutil.copytree(tools / "dotnet/shared", output / "runtime/shared")
            shutil.copy2(tools / "dotnet/dotnet", output / "runtime/dotnet")
        else:
            raise ValueError(name)
        if name in {"zplr", "zpl-renderer-js", "zebrash-ts", "codyps-zpl-node"}:
            driver = output if name == "zplr" else output / "node"
            shutil.copy2(root / "benchmarks/adapters/node/session.mjs", driver / "session.mjs")
        if name in {"zplr", "zpl-renderer-js", "zebrash-ts", "codyps-zpl-node", "binarykits"}:
            (output / "session.json").write_text('{"protocol": 1}\n')
        size = source_size(root, name, Path(spec["native"]).resolve() if spec.get("native") else None)
        deployed = [p for p in output.rglob("*") if p.is_file() and "runtime" not in p.relative_to(output).parts]
        size["artifact_bytes"] = sum(p.stat().st_size for p in deployed)
        size["artifact_manifest"] = [dict(name=str(p.relative_to(output)), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(deployed)]
        (output / "size.json").write_text(json.dumps(size) + "\n")
        # Runtime invocation is relocatable; no sandbox paths are embedded in metadata.
        command = (
            ["runtime/bin/node", "main.mjs", "zplr"]
            if name == "zplr"
            else ["runtime/bin/node", "node/renderers.mjs", "--library=" + name]
            if name in ["zpl-renderer-js", "zebrash-ts", "codyps-zpl-node"]
            else ["runtime/dotnet", "Comparison.dll"]
            if name == "binarykits"
            else ["adapter"]
        )
        (output / "command.json").write_text(json.dumps(command) + "\n")
        identities = [
            {
                "name": str(p.relative_to(output)),
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            }
            for p in sorted(output.rglob("*"))
            if p.is_file()
        ]
        (output / "identity.json").write_text(json.dumps(identities) + "\n")


if __name__ == "__main__":
    build(json.loads(Path(sys.argv[1]).read_text()), sys.argv[2])
