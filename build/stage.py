"""Run a report stage in a private tree; publish only newly written artifacts."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def stage(spec, destination):
    output = Path(destination).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="zpl-report-", dir=os.environ.get("ZPL_BUILD_TMPDIR")) as temporary:
        # Assembly publishes every input. Populate its declared output directly
        # instead of hashing and copying the entire report tree a second time.
        assemble = spec.get("assemble", False)
        root = output if assemble else Path(temporary)

        def copy(source, relative):
            source = Path(source)
            target = root / relative
            if source.is_dir() and relative.endswith(".png"):
                if (source / "image.png").exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source / "image.png", target)
            elif source.is_dir():
                # Bazel tree artifacts are read-only. Copy their contents, not
                # their modes: a later report stage may replace an earlier page.
                for child in source.rglob("*"):
                    if child.is_file():
                        copied = target / child.relative_to(source)
                        copied.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(child, copied)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)

        for source, relative in spec["inputs"]:
            copy(source, relative)
        before = {} if assemble else {
            p.relative_to(root): hashlib.sha256(p.read_bytes()).digest()
            for p in root.rglob("*")
            if p.is_file()
        }
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "MPLBACKEND": "Agg",
            "MPLCONFIGDIR": str(Path(temporary) / "_cache"),
            "HOME": str(Path(temporary) / "_cache"),
            "XDG_CACHE_HOME": str(Path(temporary) / "_cache"),
        }
        env["PYTHONPATH"] = os.pathsep.join(
            [str(root / "benchmarks"), str(root)]
            + [str(Path(p).resolve()) for p in sys.path if p]
        )
        for command in spec.get("commands", []):
            subprocess.run([sys.executable, *command], cwd=root, env=env, check=True)
        if assemble:
            return
        for path in root.rglob("*"):
            if not path.is_file() or path.relative_to(root).parts[0] == "_cache":
                continue
            relative = path.relative_to(root)
            if before.get(relative) != hashlib.sha256(path.read_bytes()).digest():
                target = output / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)


if __name__ == "__main__":
    stage(json.loads(Path(sys.argv[1]).read_text()), sys.argv[2])
