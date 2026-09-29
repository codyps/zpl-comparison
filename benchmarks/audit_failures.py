"""Inventory execution failures and comparisons without matching ink or canvases."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path

SUITES = {
    "accuracy": "accuracy/results.json",
    "conformance": "accuracy/comparisons/features/results.json",
    "layout-accuracy": "accuracy/comparisons/layout/results.json",
    "external-zpl": "accuracy/comparisons/external/results.json",
    "zq610-candidates": "zq610-candidates/results.json",
}


def failure_kinds(row):
    kinds = []
    if row["status"] not in ("rendered", "blank"):
        kinds.append("execution_" + row["status"])
    if row.get("dimensions_match") is False:
        kinds.append("canvas_mismatch")
    if row.get("reference_ink", 0) > 0:
        if row["status"] == "blank":
            kinds.append("blank_against_ink")
        elif row["status"] == "rendered" and row.get("iou") == 0:
            kinds.append("zero_ink_overlap")
    return kinds


def inventory(root):
    failures, counts = [], {}
    for suite, relative in SUITES.items():
        data = json.loads((root / "docs/benchmarks" / relative).read_text())
        for row in data["results"]:
            key = suite + "/" + row["library"]
            count = counts.setdefault(key, Counter())
            count["observations"] += 1
            count["status_" + row["status"]] += 1
            if row.get("score") is None:
                count["unscored"] += 1
            kinds = failure_kinds(row)
            count.update(kinds)
            if kinds:
                failures.append(dict(suite=suite, library=row["library"], case=row["case"],
                                     validity=row.get("validity", "unspecified"), kinds=kinds,
                                     diagnostic=row.get("diagnostic") or row.get("error") or row.get("stderr", "")))
    return dict(counts=counts, failures=failures)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("bazel-bin/reports_saved"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = inventory(args.input)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    with args.output.with_suffix(".tsv").open("w") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["suite", "library", "case", "validity", "failures"])
        for row in data["failures"]:
            writer.writerow([row[k] for k in ["suite", "library", "case", "validity"]] + [",".join(row["kinds"])])
    print(sum(c["observations"] for c in data["counts"].values()), "observations;", len(data["failures"]), "flagged rows")


if __name__ == "__main__":
    main()
