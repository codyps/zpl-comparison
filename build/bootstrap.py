"""Repository fetch phase only: download locked dependencies, never compile adapters."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import tomllib

kind, tools, raw, local_source = sys.argv[1:]
tools = Path(tools)
files = {k: Path(v) for k, v in json.loads(raw).items()}
root = Path.cwd()
env = {**os.environ, "HOME": str(root / "home"), "DOTNET_CLI_TELEMETRY_OPTOUT": "1"}
env["PATH"] = os.pathsep.join(
    [str(tools / p / "bin") for p in ["rust", "go", "node"]] + [env["PATH"]]
)


def run(*args, cwd=None):
    subprocess.run(list(map(str, args)), cwd=cwd, env=env, check=True)


def copy(key, dest):
    dest = root / dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(files[key], dest)


def source(name, dest):
    spec = json.loads(files["benchmarks/sources.lock.json"].read_text())[name]
    run("git", "init", "--initial-branch=main", dest)
    url = (
        local_source
        if name == "zpl" and local_source
        else spec.get("fetch_url", spec["url"])
    )
    run("git", "-C", dest, "fetch", "--depth=1", url, spec["rev"])
    run("git", "-C", dest, "checkout", "--detach", "FETCH_HEAD")
    actual = subprocess.check_output(
        ["git", "-C", str(dest), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual != spec["rev"]:
        raise ValueError("Source revision mismatch")
    shutil.rmtree(dest / ".git")


if kind == "rust":
    copy("benchmarks/adapters/rust/Cargo.toml", "benchmarks/adapters/rust/Cargo.toml")
    copy("benchmarks/adapters/rust/Cargo.lock", "benchmarks/adapters/rust/Cargo.lock")
    source("zpl", root / "benchmarks/_work/zpl")
    # Cargo needs bin paths to resolve the manifest, but these are not build inputs.
    dummy = root / "benchmarks/adapters/rust/src/main.rs"
    dummy.parent.mkdir(parents=True)
    dummy.write_text("fn main() {}\n")
    env["CARGO_HOME"] = str(root / "cargo-home")
    run(
        "cargo",
        "vendor",
        "--locked",
        "--manifest-path",
        root / "benchmarks/adapters/rust/Cargo.toml",
        root / "vendor",
    )
    config = root / "cargo-home/config.toml"
    config.write_text(
        '[source.crates-io]\nreplace-with="vendored"\n[source.vendored]\ndirectory='
        + json.dumps(str(root / "vendor"))
        + "\n"
    )
    original = tomllib.loads(files["benchmarks/adapters/rust/Cargo.toml"].read_text())
    groups = {}
    for name in ["codyps-zpl", "labelize", "forge", "ffi"]:
        folder = root / "manifests" / name
        folder.mkdir(parents=True)
        dependency = original["dependencies"][name].copy()
        if "path" in dependency:
            dependency["path"] = "../../benchmarks/_work/zpl/zpl"
        encoded = ", ".join(k + "=" + json.dumps(v) for k, v in dependency.items())
        # Shared adapter sources mention every feature. Keep those names known to
        # rustc while resolving only this adapter's dependency closure.
        features = "\n".join(
            json.dumps(feature) + "=" + json.dumps(["dep:" + name] if feature == name else [])
            for feature, spec in original["dependencies"].items()
            if spec.get("optional")
        )
        manifest = (
            '[package]\nname="zpl-comparison"\nversion="0.0.0"\nedition="2021"\n[workspace]\n[dependencies]\n'
            + name
            + "={"
            + encoded
            + "}\n[features]\n"
            + features
            + "\n[[bin]]\nname="
            + json.dumps(name)
            + '\npath="src/main.rs"\nrequired-features=['
            + json.dumps(name)
            + "]\n[profile.release]\nstrip=true\n"
        )
        (folder / "Cargo.toml").write_text(manifest)
        shutil.copyfile(
            files["benchmarks/adapters/rust/Cargo.lock"], folder / "Cargo.lock"
        )
        (folder / "src").mkdir()
        (folder / "src/main.rs").write_text("fn main() {}\n")
        metadata = json.loads(
            subprocess.check_output(
                [
                    "cargo",
                    "metadata",
                    "--offline",
                    "--format-version=1",
                    "--features",
                    name,
                    "--manifest-path",
                    str(folder / "Cargo.toml"),
                ],
                env=env,
            )
        )
        paths = sorted(
            {
                str(Path(p["manifest_path"]).parent.relative_to(root)) + "/**"
                for p in metadata["packages"]
                if p.get("source")
            }
        )
        # The action uses the conventional adapter location; the path dependency stays identical.
        if name == "codyps-zpl":
            (folder / "Cargo.toml").write_text(
                manifest.replace(
                    "../../benchmarks/_work/zpl/zpl", "../../_work/zpl/zpl"
                )
            )
            paths.append("benchmarks/_work/zpl/**")
        paths += [
            "manifests/" + name + "/Cargo.toml",
            "manifests/" + name + "/Cargo.lock",
        ]
        groups[name] = paths
        shutil.rmtree(folder / "src")
    (root / "groups.json").write_text(json.dumps(groups))
    shutil.rmtree(root / "cargo-home")
    dummy.unlink()
elif kind == "go":
    copy("benchmarks/adapters/go/go.mod", "benchmarks/adapters/go/go.mod")
    copy("benchmarks/adapters/go/go.sum", "benchmarks/adapters/go/go.sum")
    source("go-zpl", root / "benchmarks/_work/go-zpl")
    env.update(
        GOMODCACHE=str(root / "modules"),
        GOPATH=str(root / "go-home"),
        GOTOOLCHAIN="local",
    )
    for cwd in [root / "benchmarks/adapters/go", root / "benchmarks/_work/go-zpl"]:
        run("go", "mod", "download", "all", cwd=cwd)
elif kind == "zebrash":
    for name in ["go.mod", "go.sum"]:
        copy("benchmarks/adapters/zebrash/" + name, "benchmarks/adapters/zebrash/" + name)
    source("zebrash", root / "benchmarks/_work/zebrash")
    env.update(GOMODCACHE=str(root / "modules"), GOPATH=str(root / "go-home"), GOTOOLCHAIN="local")
    run("go", "mod", "download", "all", cwd=root / "benchmarks/adapters/zebrash")
elif kind in ["zpl-renderer-js", "zebrash-ts"]:
    source(kind, root / "benchmarks/_work" / kind)
    for name in ["package.json", "package-lock.json"]:
        copy("benchmarks/adapters/" + kind + "/" + name, name)
    env["npm_config_cache"] = str(root / "npm-cache")
    run("npm", "ci", "--ignore-scripts")
    shutil.rmtree(root / "npm-cache")
elif kind == "codyps-zpl-node":
    checkout = root / "benchmarks/_work/codyps-zpl-node"
    source("zpl", checkout)
    env["CARGO_HOME"] = str(root / "cargo-home")
    run("cargo", "vendor", "--locked", "--manifest-path", checkout / "Cargo.toml", root / "vendor")
    shutil.rmtree(root / "cargo-home")
elif kind == "node":
    source("zplr", root / "benchmarks/_work/zplr")
    for name in ["package.json", "package-lock.json"]:
        copy("benchmarks/adapters/node/" + name, name)
    env["npm_config_cache"] = str(root / "npm-cache")
    run("npm", "ci", "--ignore-scripts")
    run("node", "lib/prebuild.mjs", "download", cwd=root / "node_modules/skia-canvas")
    shutil.rmtree(root / "npm-cache")
elif kind == "dotnet":
    source("BinaryKits.Zpl", root / "benchmarks/_work/BinaryKits.Zpl")
    for name in ["Comparison.csproj", "packages.lock.json"]:
        copy("benchmarks/adapters/dotnet/" + name, name)
    feed = root / "packages"
    feed.mkdir()
    packages = json.loads((root / "packages.lock.json").read_text())["dependencies"]["net8.0"]
    for name, package in packages.items():
        name = name.lower()
        version = package["resolved"].lower()
        filename = f"{name}.{version}.nupkg"
        archive = feed / filename
        run("curl", "--fail", "--silent", "--show-error", "--location", "--retry", "3", "https://api.nuget.org/v3-flatcontainer/" + name + "/" + version + "/" + filename, "--output", archive)
        # NuGet --locked-mode verifies the canonical package content hash during
        # the offline restore action. It is not the signed ZIP's raw SHA-512.

else:
    raise ValueError(kind)
shutil.rmtree(root / "home", ignore_errors=True)
