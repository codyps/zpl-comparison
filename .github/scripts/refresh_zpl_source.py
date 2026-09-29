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


if __name__ == "__main__":
    # Locate Cargo in the same pinned toolchain used by renderer compilation.
    files = subprocess.check_output(
        ["bazel", "cquery", "@native_tools//:rust", "--output=files"], text=True
    ).splitlines()
    execution_root = subprocess.check_output(["bazel", "info", "execution_root"], text=True).strip()
    cargo = next(Path(execution_root) / p for p in files if p.endswith("/bin/cargo"))
    refresh(Path.cwd(), cargo)
