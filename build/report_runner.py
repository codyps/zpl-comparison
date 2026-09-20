"""Run the existing offline pipeline in a private, declared output tree."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    manifest = Path(sys.argv[1])
    output = Path(sys.argv[2]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    for source, relative in json.loads(manifest.read_text()):
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        # Copies, never symlinks: generators may overwrite their staged inputs.
        shutil.copyfile(source, target)

    env = os.environ.copy()
    # Child scripts use the same Bazel interpreter and resolved wheel closure.
    env["PYTHONPATH"] = os.pathsep.join(
        [str(output / "benchmarks"), str(output)]
        + [str(Path(p).resolve()) for p in sys.path if p]
    )
    with tempfile.TemporaryDirectory(prefix="zpl-report-cache-") as cache:
        env.update(MPLCONFIGDIR=cache, HOME=cache, XDG_CACHE_HOME=cache)
        subprocess.run(
            [sys.executable, str(output / "benchmarks/regenerate.py")],
            cwd=output,
            env=env,
            check=True,
        )


if __name__ == "__main__":
    main()
