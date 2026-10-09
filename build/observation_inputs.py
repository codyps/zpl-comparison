"""Stable, per-adapter input identities for replaying CI observations."""

import hashlib
import json
from pathlib import Path
import sys

LIBRARIES = ["codyps-zpl", "labelize", "forge", "go", "ffi", "binarykits", "zplr", "zebrash", "zpl-renderer-js", "zebrash-ts", "codyps-zpl-node"]
SOURCE = {"codyps-zpl-node": "zpl", "codyps-zpl": "zpl", "labelize": "labelize", "forge": "zpl-forge",
          "go": "go-zpl", "ffi": "go-zpl", "binarykits": "BinaryKits.Zpl", "zplr": "zplr",
          "zebrash": "zebrash", "zpl-renderer-js": "zpl-renderer-js", "zebrash-ts": "zebrash-ts"}


def identities(files, probe=False, python_version=""):
    locks = json.loads(Path(files["benchmarks/sources.lock.json"]).read_text())
    result = {}
    for library in LIBRARIES:
        language = "rust" if library in {"codyps-zpl", "labelize", "forge", "ffi"} else "go" if library == "go" else "dotnet" if library == "binarykits" else "node"
        prefixes = ["benchmarks/adapters/" + language + "/"]
        if library in {"zebrash", "zpl-renderer-js", "zebrash-ts", "codyps-zpl-node"}:
            prefixes = ["benchmarks/adapters/" + library + "/"]
            if library != "zebrash":
                prefixes.extend(["benchmarks/adapters/node/renderers.mjs", "benchmarks/adapters/node/session.mjs"])
        if library == "ffi":
            prefixes.append("benchmarks/adapters/go/")
        selected = {name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                    for name, path in sorted(files.items())
                    if name in {"build/render.py", "build/renderer_session.py", "build/native_build.py", "build/bootstrap.py", "build/toolchains.lock.json",
                                "build/native.bzl", "build/requirements.lock.txt", "benchmarks/accuracy/pixels.py"}
                    or (library == "binarykits" and name in {"build/dotnet_runtime.py", "build/dotnet_deps.bzl", "build/dotnet_toolchain.BUILD", "build/patches/rules_dotnet-hermetic-publish.patch", "MODULE.bazel"})
                    or (probe and name in {"build/probe.py", "benchmarks/invalid.py"})
                    or any(name.startswith(prefix) for prefix in prefixes)}
        value = dict(source=locks[SOURCE[library]], files=selected, python_version=python_version)
        result[library] = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    return result


if __name__ == "__main__":
    print(json.dumps(identities(json.loads(sys.argv[1]), probe=sys.argv[2] == "probe", python_version=sys.argv[3]), sort_keys=True))
