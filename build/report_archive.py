"""Transport final reports as deterministic archives; materialize them locally."""

import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile

from build.stage import stage


def pack(spec, destination):
    with tempfile.TemporaryDirectory(prefix="zpl-archive-", dir=os.environ.get("ZPL_BUILD_TMPDIR")) as temporary:
        root = Path(temporary) / "report"
        stage(spec, root)
        # Remote-cache compression handles transport. Avoid compressing twice.
        with tarfile.open(destination, "w", format=tarfile.PAX_FORMAT) as archive:
            for path in sorted(root.rglob("*")):
                relative = path.relative_to(root).as_posix()
                member = tarfile.TarInfo(relative)
                member.mode = 0o755 if path.is_dir() else 0o644
                if path.is_dir():
                    member.type = tarfile.DIRTYPE
                    archive.addfile(member)
                else:
                    member.size = path.stat().st_size
                    with path.open("rb") as source:
                        archive.addfile(member, source)


def unpack(source, destination):
    Path(destination).mkdir(parents=True, exist_ok=True)
    with tarfile.open(source, "r|") as archive:
        archive.extractall(destination, filter="data")


if __name__ == "__main__":
    spec = json.loads(Path(sys.argv[1]).read_text())
    if "archive" in spec:
        unpack(spec["archive"], sys.argv[2])
    else:
        pack(spec, sys.argv[2])
