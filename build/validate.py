"""Validate saved references and ensure checked fixture bytes match their generators."""

import hashlib
import subprocess
import sys
from pathlib import Path

from accuracy.run import corpus, sha
from conformance import load_cases, reference_images

root = Path.cwd()
corpus()
for name, directory in [
    ("render-conformance", "conformance-reference"),
    ("external-zpl", "external-reference"),
]:
    manifest, cases = load_cases(root / "test-data" / name, invalid=True)
    reference_dir = root / "benchmarks/accuracy" / directory
    reference, refs = reference_images(reference_dir, cases)
    if reference.get("corpus_sha256") != sha(
        root / "test-data" / name / "manifest.json"
    ):
        raise ValueError("Stale printer capture corpus: " + name)
    failures = {row["name"]: row for row in reference.get("failures", [])}
    for case in cases:
        if (
            case.get("capture_eligible", True)
            and case["validity"] != "invalid"
            and case["name"] not in refs
        ):
            failure = failures.get(case["name"])
            if (
                not failure
                or failure["zpl_sha256"] != case["sha256"]
                or sha(reference_dir / (case["name"] + ".zpl")) != case["sha256"]
            ):
                raise ValueError(
                    "Missing or stale printer failure record: " + case["name"]
                )
for directory in ["render-conformance", "invalid-zpl"]:
    path = root / "test-data" / directory

    def snapshot(path=path):
        return {
            str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob("*")
            if p.is_file() and (p.suffix == ".zpl" or p.name == "manifest.json")
        }

    before = snapshot()
    subprocess.run([sys.executable, str(path / "generate.py")], check=True)
    if snapshot() != before:
        raise ValueError(
            "Stale fixture sources: run test-data/"
            + directory
            + "/generate.py and include the updated manifest/cases"
        )
