"""Record a checked-out ZPL revision and resolve its adapter dependencies for CI."""
import json
import os
from pathlib import Path
import subprocess
import tomllib


def refresh(root, cargo):
    root = Path(root).resolve()
    source = root / "benchmarks/_work/zpl"
    revision = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    if subprocess.check_output(
        ["git", "-C", str(source), "status", "--porcelain"], text=True
    ).strip():
        raise ValueError("ZPL source checkout must be clean")
    package = tomllib.loads((source / "zpl/Cargo.toml").read_text())["package"]
    version = package["version"]
    if isinstance(version, dict):
        version = tomllib.loads((source / "Cargo.toml").read_text())["workspace"]["package"]["version"]
    env = {**os.environ, "PATH": str(Path(cargo).resolve().parent) + os.pathsep + os.environ["PATH"]}
    # Keep existing resolutions where possible; accommodate new upstream dependencies.
    subprocess.run(
        [str(cargo), "metadata", "--format-version=1", "--manifest-path",
         str(root / "benchmarks/adapters/rust/Cargo.toml")],
        env=env, stdout=subprocess.DEVNULL, check=True,
    )
    lock = root / "benchmarks/sources.lock.json"
    data = json.loads(lock.read_text())
    data["zpl"].update(rev=revision, version=version)
    lock.write_text(json.dumps(data, indent=2) + "\n")
    print(f"codyps/zpl {version} at {revision}")


def pinned_cargo():
    # Locate Cargo in the same pinned toolchain used by renderer compilation.
    files = subprocess.check_output(
        ["bazel", "cquery", "@native_tools//:rust", "--output=files"], text=True
    ).splitlines()
    # cquery fetches external repositories but does not populate the execroot's
    # symlink forest on a fresh runner. Use the fetched repository directly.
    # https://bazel.build/remote/output-directories#layout-diagram
    output_base = subprocess.check_output(["bazel", "info", "output_base"], text=True).strip()
    cargo = next(Path(output_base) / p for p in files
                 if p.startswith("external/") and p.endswith("/rust/bin/cargo"))
    if not cargo.is_file():
        raise FileNotFoundError(f"Pinned Cargo was not fetched: {cargo}")
    return cargo


if __name__ == "__main__":
    refresh(Path.cwd(), pinned_cargo())
