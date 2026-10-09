"""Build adapters offline, or assemble outputs supplied by language rules."""

import hashlib
import json
import shutil
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
    # Keep packaging scratch on Bazel's output filesystem, independent of host /tmp.
    with tempfile.TemporaryDirectory(prefix="zpl-package-", dir=output.parent) as temporary:
        root = Path(temporary)
        for source, relative in spec["inputs"]:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if Path(source).is_dir():
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                shutil.copyfile(source, target)
                target.chmod(Path(source).stat().st_mode)
        tools = Path(spec["tools"]).resolve() if spec["tools"] else None
        name = spec["library"]
        if (root / "built/adapter").exists():
            shutil.copy2(root / "built/adapter", output / "adapter")
            if name == "ffi":
                for path in (root / "built").glob("libzpl.*"):
                    shutil.copy2(path, output / path.name)
        elif name == "go-native":
            for path in (root / "built").glob("libzpl.*"):
                shutil.copy2(path, output / path.name)
        elif name == "codyps-zpl-node":
            checkout = root / "benchmarks/_work/codyps-zpl-node"
            package = output / name
            package.mkdir()
            for filename in ["package.json", "index.cjs", "index.mjs", "index.d.ts"]:
                shutil.copy2(checkout / "zpl-node" / filename, package / filename)
            shutil.copy2(checkout / "LICENSE", package / "LICENSE")
            shutil.copytree(root / "built/pkg", package / "pkg")
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
