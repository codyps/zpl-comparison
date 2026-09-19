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
    steps += [
        ["benchmarks/accuracy/gallery.py", output, "--check"],
        ["benchmarks/compatibility.py"],
        ["benchmarks/compatibility.py", "--check"],
    ]
    for step in steps:
        print("+", sys.executable, *step, flush=True)
        subprocess.run([sys.executable, *step], cwd=REPO, check=True)


if __name__ == "__main__":
    main()
