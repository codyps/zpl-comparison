"""Aggregate independently cached probe pairs and regenerate the behavior report."""

import json
from pathlib import Path
import platform

from benchmarks.invalid import load_cases, render_report
from benchmarks.accuracy.pixels import sha


def main():
    manifest = load_cases()
    rows = [json.loads(p.read_text()) for p in sorted(Path("_invalid_rows").glob("*.json"))]
    lanes = {}
    for row in rows:
        lanes.setdefault(row["library"], set()).add(row["mode"])
    data = dict(schema=1, suite=manifest["suite"], cases=manifest["cases"],
                manifest_sha256=sha(Path("test-data/invalid-zpl/manifest.json")),
                repeats=2, timeout_seconds=10, lanes={lib: sorted(modes) for lib, modes in sorted(lanes.items())},
                measured_utc=max((r["observed_utc"] for r in rows if r.get("observed_utc", "")[:4].isdigit()), default="unavailable"),
                host=platform.platform() if any("evidence_mode" not in r for r in rows) else "Saved trusted observations; see individual provenance",
                results=rows)
    dest = Path("docs/benchmarks/invalid")
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "results.json").write_text(json.dumps(data, indent=2) + "\n")
    (dest / "README.md").write_text(render_report(data, dest))


if __name__ == "__main__":
    main()
