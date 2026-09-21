#!/usr/bin/env python3
"""Refresh all published accuracy artifacts and dependent compatibility pages."""

import argparse
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reports-only",
        action="store_true",
        help="regenerate Markdown and plots from saved results without running adapters",
    )
    args = parser.parse_args()
    output = "docs/benchmarks/accuracy"
    steps = (
        [["benchmarks/accuracy/report.py", output]]
        if args.reports_only
        else [["benchmarks/accuracy/run.py"]]
    )
    steps.insert(0, ["benchmarks/labelary.py"])
    if not args.reports_only:
        steps += [
            [
                "benchmarks/conformance.py",
                "--only",
                "all",
                "--include-invalid",
                "--output",
                "docs/benchmarks/conformance",
            ]
        ]
    if not args.reports_only:
        steps += [
            [
                "benchmarks/conformance.py",
                "--corpus",
                "test-data/external-zpl",
                "--only",
                "all",
                "--output",
                "docs/benchmarks/external-zpl",
            ]
        ]
    steps += [
        [
            "benchmarks/conformance.py",
            "--corpus",
            "test-data/external-zpl",
            "--reports-only",
            "--output",
            "docs/benchmarks/external-zpl",
        ],
        [
            "benchmarks/conformance.py",
            "--reports-only",
            "--output",
            "docs/benchmarks/conformance",
        ],
        ["benchmarks/accuracy/features.py"],
        ["benchmarks/accuracy/features.py", "--suite", "external"],
        ["benchmarks/accuracy/features.py", "--suite", "layout"],
        ["benchmarks/accuracy/overview.py", output],
        ["benchmarks/accuracy/overview.py", output, "--check"],
        ["benchmarks/accuracy/gallery.py", output, "--check"],
        ["benchmarks/compatibility.py"],
        ["benchmarks/compatibility.py", "--check"],
    ]
    failed = False
    for step in steps:
        print("+", sys.executable, *step, flush=True)
        result = subprocess.run([sys.executable, *step], cwd=REPO)
        if result.returncode:
            if step[0] != "benchmarks/conformance.py" or "--reports-only" in step:
                raise SystemExit(result.returncode)
            failed = True  # Preserve render failures and still publish their evidence.
    if failed:
        raise SystemExit("Renderer crash/timeout; comparison reports preserved")


if __name__ == "__main__":
    main()
