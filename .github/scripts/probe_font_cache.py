"""Measure whether filesystem timestamps distinguish the font test's writes."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from build.font_profile import configure

result = {"iterations": 100, "unchanged_ctime": 0, "missed_mutation": 0}
for _ in range(result["iterations"]):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        font = root / "font.ttf"
        font.write_bytes(b"original")
        (root / "manifest.json").write_text(json.dumps({
            "sha256": {font.name: hashlib.sha256(font.read_bytes()).hexdigest()},
            "fonts": {"0": font.name},
        }))
        configure(root, "go")
        configure(root, "go")
        before = font.stat()
        font.write_bytes(b"modified")
        os.utime(font, ns=(before.st_atime_ns, before.st_mtime_ns))
        after = font.stat()
        result["unchanged_ctime"] += before.st_ctime_ns == after.st_ctime_ns
        try:
            configure(root, "go")
        except ValueError:
            pass
        else:
            result["missed_mutation"] += 1
print(json.dumps(result, sort_keys=True))
