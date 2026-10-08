#!/usr/bin/env python3
"""Fetch immutable source revisions and build isolated benchmark adapters."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "_work"
RUST = ["codyps-zpl", "toolchain", "labelize", "forge", "builder", "ffi"]
EXTRA_RENDERERS = ["codyps-zpl-node", "zebrash", "zpl-renderer-js", "zebrash-ts"]


def run(args, **kw):
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="Comma-separated adapter names; default: all")
    args = ap.parse_args()
    selected = (
        set(args.only.split(","))
        if args.only
        else set(RUST + ["go", "binarykits", "python", "jszpl", "zplr"] + EXTRA_RENDERERS)
    )
    unknown = selected - set(RUST + ["go", "binarykits", "python", "jszpl", "zplr"] + EXTRA_RENDERERS)
    if unknown:
        ap.error(f"Unknown adapters: {sorted(unknown)}")
    WORK.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.setdefault("CARGO_HOME", str(WORK / "cargo-home"))
    env.setdefault("CARGO_TARGET_DIR", str(WORK / "target"))
    env.setdefault("GOCACHE", str(WORK / "go-cache"))
    env.setdefault("GOPATH", str(WORK / "go-path"))
    env.setdefault("GOMODCACHE", str(WORK / "go-mod-cache"))
    env.setdefault("DOTNET_CLI_HOME", str(WORK / "dotnet-home"))
    env.setdefault("NUGET_PACKAGES", str(WORK / "nuget"))
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    # Download source for provenance/size analysis even for package-installed adapters.
    for name, spec in json.loads((ROOT / "sources.lock.json").read_text()).items():
        dest = WORK / name
        if not dest.exists():
            run(["git", "init", dest])
            run(["git", "-C", dest, "remote", "add", "origin", spec.get("fetch_url", spec["url"])])
        head = subprocess.run(
            ["git", "-C", dest, "rev-parse", "HEAD"], capture_output=True, text=True
        )
        if head.stdout.strip() != spec["rev"]:
            # Never overwrite modifications in a downloaded checkout.
            dirty = subprocess.check_output(
                ["git", "-C", dest, "status", "--porcelain"], text=True
            )
            if dirty:
                raise RuntimeError(f"Dirty source checkout: {dest}")
            run(["git", "-C", dest, "fetch", "--depth", "1", "origin", spec["rev"]])
            run(["git", "-C", dest, "checkout", "--detach", spec["rev"]])
    commands = {}
    if selected & {"go", "ffi"}:
        lib = WORK / ("libzpl.dylib" if os.uname().sysname == "Darwin" else "libzpl.so")
        run(
            [
                "go",
                "build",
                "-mod=readonly",
                "-buildmode=c-shared",
                "-o",
                lib,
                "./cmd/libzpl",
            ],
            cwd=WORK / "go-zpl",
            env=env,
        )
        env["LIBZPL_PATH"] = str(lib.resolve())
        # zpl-rs stages its native library beside the isolated executables.
        env["LIBZPL_COPY_TO"] = str(Path(env["CARGO_TARGET_DIR"]) / "release")
        adapter = ROOT / "adapters/go"
        run(
            [
                "go",
                "build",
                "-mod=readonly",
                "-trimpath",
                "-ldflags=-s -w",
                "-o",
                WORK / "go-adapter",
                ".",
            ],
            cwd=adapter,
            env=env,
        )
        commands["go"] = [str(WORK / "go-adapter")]
    if "zebrash" in selected:
        run(["go", "build", "-mod=readonly", "-trimpath", "-buildvcs=false", "-ldflags=-s -w",
             "-o", WORK / "zebrash-adapter", "."], cwd=ROOT / "adapters/zebrash", env=env)
        commands["zebrash"] = [str(WORK / "zebrash-adapter")]
    for name in ["zpl-renderer-js", "zebrash-ts"]:
        if name in selected:
            run(["npm", "ci", "--ignore-scripts", "--cache", WORK / "npm-cache"],
                cwd=ROOT / "adapters" / name, env=env)
            commands[name] = ["node", str(ROOT / "adapters/node/renderers.mjs"), "--library=" + name]
    if "codyps-zpl-node" in selected:
        checkout = WORK / "zpl"
        run(["bash", "scripts/build-node.sh"], cwd=checkout, env=env)
        package = ROOT / "adapters/codyps-zpl-node"
        package.mkdir(exist_ok=True)
        for filename in ["package.json", "index.cjs", "index.mjs", "index.d.ts", "LICENSE"]:
            shutil.copy2(checkout / "zpl-node" / filename, package / filename)
        shutil.copytree(checkout / "zpl-node/pkg", package / "pkg", dirs_exist_ok=True)
        commands["codyps-zpl-node"] = ["node", str(ROOT / "adapters/node/renderers.mjs"), "--library=codyps-zpl-node"]
    cargo = os.environ.get("BENCH_CARGO", "cargo")
    for name in RUST:
        if name not in selected:
            continue
        command = [
            cargo,
            "build",
            "--release",
            "--locked",
            "--manifest-path",
            ROOT / "adapters/rust/Cargo.toml",
            "--features",
            name,
            "--bin",
            name,
        ]
        run(command, env=env)
        commands[name] = [str(Path(env["CARGO_TARGET_DIR"]) / "release" / name)]
    if selected & {"jszpl", "zplr"}:
        run(
            ["npm", "ci", "--cache", WORK / "npm-cache"],
            cwd=ROOT / "adapters/node",
            env=env,
        )
        # npm 11+ may gate lifecycle scripts. Install this explicitly pinned
        # native renderer using its own verified prebuilt installer.
        run(
            ["node", "lib/prebuild.mjs", "download"],
            cwd=ROOT / "adapters/node/node_modules/skia-canvas",
            env=env,
        )
        for name in ["jszpl", "zplr"]:
            if name in selected:
                commands[name] = ["node", str(ROOT / "adapters/node/main.mjs"), name]
    if "python" in selected:
        commands["python"] = [os.sys.executable, str(ROOT / "adapters/python.py")]
    if "binarykits" in selected:
        dotnet = os.environ.get("BENCH_DOTNET", "dotnet")
        restore = [
            dotnet,
            "restore",
            ROOT / "adapters/dotnet/Comparison.csproj",
            "--locked-mode",
        ]
        if os.environ.get("BENCH_NUGET_SOURCE"):
            restore += ["--source", os.environ["BENCH_NUGET_SOURCE"]]
        run(restore, env=env)
        run(
            [
                dotnet,
                "publish",
                ROOT / "adapters/dotnet/Comparison.csproj",
                "--no-restore",
                "-c",
                "Release",
                "-o",
                WORK / "dotnet-out",
            ],
            env=env,
        )
        commands["binarykits"] = [dotnet, str(WORK / "dotnet-out/Comparison.dll")]
    # Keep adapter-specific loader settings explicit in the saved local config.
    config = {
        "commands": commands,
        "environment": {
            k: env[k]
            for k in [
                "CARGO_HOME",
                "CARGO_TARGET_DIR",
                "DOTNET_CLI_HOME",
                "NUGET_PACKAGES",
            ]
        },
    }
    release = str(Path(env["CARGO_TARGET_DIR"]) / "release")
    config["environment"].update(
        {"DYLD_LIBRARY_PATH": release, "LD_LIBRARY_PATH": release}
    )
    (WORK / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    run(
        [
            cargo,
            "metadata",
            "--locked",
            "--format-version",
            "1",
            "--manifest-path",
            ROOT / "adapters/rust/Cargo.toml",
            "--all-features",
        ],
        env=env,
        stdout=(WORK / "cargo-metadata.json").open("w"),
    )


if __name__ == "__main__":
    main()
