#!/usr/bin/env python3
"""Rebuild every derived benchmark resource from collected evidence."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]

# Order matters: corpus manifests precede reports; feature scores precede compatibility.
FIXTURES = [
    ["test-data/render-conformance/generate.py"],
    ["test-data/layout-accuracy/generate.py"],
    ["test-data/invalid-zpl/generate.py"],
]
REPORTS = [
    [
        "benchmarks/conformance.py",
        "--corpus", "test-data/layout-accuracy",
        "--reports-only",
        "--output", "docs/benchmarks/layout-accuracy",
    ],
    ["benchmarks/catalog.py"],
    ["benchmarks/support.py", "--reports-only"],
    ["benchmarks/report.py", "docs/benchmarks"],
    ["benchmarks/invalid.py", "--report-only"],
    ["benchmarks/invalid.py", "--check"],
    ["benchmarks/labelary.py"],
    [
        "benchmarks/conformance.py",
        "--reports-only",
        "--output",
        "docs/benchmarks/conformance",
    ],
    [
        "benchmarks/conformance.py",
        "--corpus",
        "test-data/external-zpl",
        "--reports-only",
        "--output",
        "docs/benchmarks/external-zpl",
    ],
    ["benchmarks/accuracy/report.py", "docs/benchmarks/accuracy"],
    ["benchmarks/accuracy/features.py"],
    ["benchmarks/accuracy/features.py", "--suite", "external"],
    ["benchmarks/accuracy/features.py", "--suite", "layout"],
    ["benchmarks/accuracy/overview.py", "docs/benchmarks/accuracy"],
    ["benchmarks/accuracy/overview.py", "docs/benchmarks/accuracy", "--check"],
    ["benchmarks/compatibility.py"],
    ["benchmarks/compatibility.py", "--check"],
]
MEASUREMENTS = [
    (
        [
            "benchmarks/conformance.py",
            "--corpus", "test-data/layout-accuracy",
            "--only", "all",
            "--reference", "benchmarks/accuracy/layout-reference",
            "--output", "docs/benchmarks/layout-accuracy",
        ],
        "docs/benchmarks/layout-accuracy/results.json",
    ),
    (["benchmarks/support.py"], "docs/benchmarks/command-support.json"),
    (["benchmarks/run.py"], "docs/benchmarks/results.json"),
    (
        ["benchmarks/invalid.py", "--fail-on-crash"],
        "docs/benchmarks/invalid/results.json",
    ),
    (["benchmarks/accuracy/run.py"], "docs/benchmarks/accuracy/results.json"),
    (
        [
            "benchmarks/conformance.py",
            "--only",
            "all",
            "--include-invalid",
            "--output",
            "docs/benchmarks/conformance",
        ],
        "docs/benchmarks/conformance/results.json",
    ),
    (
        [
            "benchmarks/conformance.py",
            "--corpus",
            "test-data/external-zpl",
            "--only",
            "all",
            "--output",
            "docs/benchmarks/external-zpl",
        ],
        "docs/benchmarks/external-zpl/results.json",
    ),
]


def run(step):
    print("+", sys.executable, *step, flush=True)
    return subprocess.run([sys.executable, *step], cwd=REPO).returncode


def preflight_measurements():
    from accuracy.run import preflight
    from prepare import RUST, EXTRA_RENDERERS

    cfg = json.loads((REPO / "benchmarks/_work/config.json").read_text())
    expected = set(RUST + ["go", "binarykits", "python", "jszpl", "zplr"] + EXTRA_RENDERERS)
    missing = expected - cfg["commands"].keys()
    if missing:
        raise ValueError(
            f"Build all adapters with benchmarks/prepare.py first; missing: {sorted(missing)}"
        )
    preflight(cfg, sorted(expected))


def regenerate(measure=False):
    if measure:
        preflight_measurements()
    for step in FIXTURES:
        if status := run(step):
            return status
    failed = False
    if measure:
        for step, filename in MEASUREMENTS:
            snapshot = REPO / filename
            before = snapshot.read_bytes() if snapshot.exists() else None
            status = run(step)
            if status:
                # Only these runners deliberately fail after saving observed failures.
                # A missing/unchanged snapshot indicates a harness failure: stop instead
                # of combining old evidence with a failed measurement attempt.
                if (
                    step[0]
                    not in {"benchmarks/conformance.py", "benchmarks/invalid.py"}
                    or not snapshot.exists()
                    or snapshot.read_bytes() == before
                ):
                    return status
                json.loads(snapshot.read_text())
                failed = True
    for step in REPORTS:
        if step[0] == "benchmarks/report.py" and not (REPO / "docs/benchmarks/results.json").exists():
            continue
        if status := run(step):
            return status
    if failed:
        print(
            "All derived resources regenerated; collected execution failures remain in the reports.",
            file=sys.stderr,
        )
        return 1
    print(
        "All derived resources regenerated, including docs/benchmarks/accuracy/accuracy.svg"
    )
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--measure",
        action="store_true",
        help="Collect fresh local performance, source-support, invalid-input and renderer results using prepared adapters before rebuilding reports; printer and SaaS captures are explicit separate steps",
    )
    args = parser.parse_args()
    raise SystemExit(regenerate(args.measure))


if __name__ == "__main__":
    main()
