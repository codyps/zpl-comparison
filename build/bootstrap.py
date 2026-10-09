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
    # Compilation dependencies belong to crate_universe. These archives are only
    # implementation source for size accounting and support reports.
    import hashlib
    import tarfile
    source("zpl", root / "benchmarks/_work/zpl")
    packages = tomllib.loads(files["benchmarks/adapters/rust/Cargo.lock"].read_text())["package"]
    groups = {"codyps-zpl": ["benchmarks/_work/zpl/**"]}
    for adapter, name in [("labelize", "labelize"), ("forge", "zpl-forge"), ("ffi", "zpl-rs"), ("builder", "zpl-builder")]:
        package = next(p for p in packages if p["name"] == name)
        version = package["version"]
        archive = root / (name + ".crate")
        run("curl", "--fail", "--silent", "--show-error", "--location", "--retry", "3",
            f"https://static.crates.io/crates/{name}/{name}-{version}.crate", "--output", archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != package["checksum"]:
            raise ValueError("Crate source checksum mismatch: " + name)
        with tarfile.open(archive) as tar:
            tar.extractall(root / "vendor", filter="data")
        archive.unlink()
        groups[adapter] = [f"vendor/{name}-{version}/**"]
    (root / "groups.json").write_text(json.dumps(groups))
elif kind == "go":
    source("go-zpl", root / "benchmarks/_work/go-zpl")
elif kind == "zebrash":
    source("zebrash", root / "benchmarks/_work/zebrash")
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

else:
    raise ValueError(kind)
shutil.rmtree(root / "home", ignore_errors=True)
