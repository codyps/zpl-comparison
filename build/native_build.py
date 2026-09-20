"""Compile one adapter from declared sources and downloaded dependencies, offline."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def build(spec, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="zpl-build-") as temporary:
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
            "DOTNET_CLI_HOME": str(root / "home"),
            "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
            "DOTNET_GENERATE_ASPNET_CERTIFICATE": "false",
            "NUGET_PACKAGES": str(root / "nuget-cache"),
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
        elif name in ["go", "go-native"]:
            if name == "go-native":
                filename = "libzpl.dylib" if sys.platform == "darwin" else "libzpl.so"
                run(
                    "go",
                    "build",
                    "-mod=readonly",
                    "-trimpath",
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
                    "-ldflags=-s -w",
                    "-o",
                    output / "adapter",
                    ".",
                    cwd=root / "benchmarks/adapters/go",
                )
        elif name == "zplr":
            shutil.copytree(root / "node_modules", output / "node_modules")
            shutil.copy2(
                root / "benchmarks/adapters/node/main.mjs", output / "main.mjs"
            )
            shutil.copytree(tools / "node", output / "runtime", symlinks=True)
        elif name == "binarykits":
            project = root / "benchmarks/adapters/dotnet/Comparison.csproj"
            run(
                tools / "dotnet/dotnet",
                "restore",
                project,
                "--locked-mode",
                "--source",
                root / "packages",
            )
            run(
                tools / "dotnet/dotnet",
                "publish",
                project,
                "--no-restore",
                "-c",
                "Release",
                "-o",
                output,
            )
            shutil.copytree(tools / "dotnet/host", output / "runtime/host")
            shutil.copytree(tools / "dotnet/shared", output / "runtime/shared")
            shutil.copy2(tools / "dotnet/dotnet", output / "runtime/dotnet")
        else:
            raise ValueError(name)
        # Runtime invocation is relocatable; no sandbox paths are embedded in metadata.
        command = (
            ["runtime/bin/node", "main.mjs", "zplr"]
            if name == "zplr"
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
