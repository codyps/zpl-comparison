#!/usr/bin/env python3
"""Publish feature renders and printer diffs using the shared accuracy metric."""

import argparse
import json
import os
from pathlib import Path
import statistics
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conformance import load_cases, reference_images
from accuracy.run import LIBRARIES, compare, gray, sha
from accuracy.presentation import LEGEND, viewport, preview
from accuracy.overview import case_page, rebase_links, score as format_score
from report import NAMES, table

REPO = Path(__file__).resolve().parents[2]
CORPUS = REPO / "test-data/render-conformance"
RENDERS = REPO / "docs/benchmarks/conformance"
REFERENCES = REPO / "benchmarks/accuracy/conformance-reference"
DEST = REPO / "docs/benchmarks/accuracy/comparisons/features"


def validate(data, cases):
    if data["manifest_sha256"] != sha(CORPUS / "manifest.json"):
        raise ValueError("Stale feature execution corpus")
    expected = {(c["name"], lib) for c in cases for lib in LIBRARIES}
    rows = {(r["case"], r["library"]): r for r in data["results"]}
    if len(rows) != len(data["results"]) or set(rows) != expected:
        raise ValueError("Expected exactly one feature result per case and renderer")
    if data["cases"] != [{k: v for k, v in c.items() if k != "path"} for c in cases]:
        raise ValueError("Stale feature case metadata")
    return rows


def generate(check=False):
    _, cases = load_cases(CORPUS, invalid=True)
    data = json.loads((RENDERS / "results.json").read_text())
    rows = validate(data, cases)
    reference_path = REFERENCES / "manifest.json"
    if reference_path.exists():
        reference, refs = reference_images(REFERENCES, cases)
        if reference.get("corpus_sha256") != sha(CORPUS / "manifest.json"):
            raise ValueError("Stale printer capture corpus")
    else:
        reference, refs = {}, {}
    failures = {r["name"]: r for r in reference.get("failures", [])}
    for case in cases:
        if (
            reference
            and case["capture_eligible"]
            and case["validity"] != "invalid"
            and case["name"] not in refs
        ):
            failure = failures.get(case["name"])
            if (
                not failure
                or failure["zpl_sha256"] != case["sha256"]
                or sha(REFERENCES / (case["name"] + ".zpl")) != case["sha256"]
            ):
                raise ValueError(
                    "Missing printer capture or failure record: " + case["name"]
                )
    results = []
    pages = {}
    legend = (
        LEGEND
        + " Blank printer references and invalid inputs are unscored; renderer failures score zero against nonblank printer references."
    )
    for number, case in enumerate(cases, 1):
        name = case["name"]
        page = DEST / "cases" / (name + ".md")

        def link(path):
            return os.path.relpath(path, page.parent)

        baseline = refs.get(name) if case["validity"] != "invalid" else None
        visible = [
            RENDERS / "images" / f"{name}-{lib}.png"
            for lib in LIBRARIES
            if rows[name, lib]["status"] in {"rendered", "blank"}
        ]
        if baseline is not None:
            visible.append(REFERENCES / (name + ".png"))
        frame = viewport(visible) if visible else (64, 64)

        def compact(path, suffix, label):
            return preview(
                path,
                DEST / "previews" / f"{name}-{suffix}.png",
                frame,
                page,
                label,
                check,
            )

        printer = (
            compact(REFERENCES / (name + ".png"), "printer", "Printer preview")
            if baseline is not None
            else "No printer preview; unscored"
        )
        content = [
            f"# {name}",
            "[Feature comparisons](../README.md) · [All accuracy comparisons](../../../README.md)",
            case["purpose"],
            f"{case['validity']} / {case.get('oracle', 'printer')} · [ZPL input]({link(case['path'])})",
            legend,
        ]
        if name.startswith("compact-"):
            content.append(
                f"[Local source provenance and inspiration]({link(CORPUS / 'INSPIRATION.md')})"
            )
        elif case.get("source"):
            content.append(
                f"[Source / inspiration]({case['source']})"
                if str(case["source"]).startswith("https://")
                else f"[Source / inspiration]({link(REPO / case['source'])})"
            )
        if case.get("notes"):
            content.append(case["notes"])
        if not case["capture_eligible"]:
            content.append(
                "Printer capture excluded: invalid input or stateful/device-dependent operations. Offline renders remain visible and unscored."
            )
        if name in failures:
            content.append("Printer preview unavailable: " + failures[name]["error"])
        for lib in LIBRARIES:
            row = rows[name, lib]
            status = row["status"]
            if status not in {"rendered", "blank", "error", "crashed", "timeout"}:
                raise ValueError("Unknown render status")
            record = dict(
                case=name,
                library=lib,
                group=case["group"],
                validity=case["validity"],
                status=status,
                score=None,
            )
            render = "Unavailable"
            difference = "Unavailable"
            if status in {"rendered", "blank"}:
                path = RENDERS / "images" / f"{name}-{lib}.png"
                raster = gray(path)
                if (row["width"], row["height"], row["ink"]) != (
                    raster.shape[1],
                    raster.shape[0],
                    int(np.count_nonzero(raster < 128)),
                ) or (status == "blank") != (row["ink"] == 0):
                    raise ValueError("Stale render dimensions/ink: " + name + "/" + lib)
                record["render_sha256"] = sha(path)
                record["image"] = str(path.relative_to(REPO))
                render = compact(path, lib, f"{NAMES[lib]} render")
                if baseline is not None:
                    metrics, diff = compare(baseline, raster)
                    record.update(metrics)
                    record["score"] = (
                        metrics["iou"] if metrics["reference_ink"] else None
                    )
                    diffpath = DEST / "images" / f"{name}-{lib}-diff.png"
                    if check:
                        with Image.open(diffpath) as image:
                            if not np.array_equal(
                                np.asarray(image.convert("RGB")), diff
                            ):
                                raise ValueError("Stale difference: " + str(diffpath))
                    else:
                        diffpath.parent.mkdir(parents=True, exist_ok=True)
                        Image.fromarray(diff).save(diffpath, optimize=True)
                    record["diff"] = str(diffpath.relative_to(REPO))
                    difference = compact(
                        diffpath, lib + "-diff", f"{NAMES[lib]} difference"
                    )
            elif baseline is not None and np.any(baseline < 128):
                record["score"] = 0.0
            label = (
                "unscored"
                if record["score"] is None
                else f"{record['score'] * 100:.2f}% IoU"
            )
            content += [
                f"## {lib}",
                f"**{NAMES[lib]}: {status}; {label}** · [All tests for this library](../libraries/{lib}.md)",
                table(
                    ["Printer preview", "Library render", "Difference"],
                    [[printer, render, difference]],
                ),
            ]
            if status not in {"rendered", "blank"}:
                content.append(
                    "~~~text\n"
                    + (row.get("diagnostic") or status).replace("~~~", "~ ~ ~")
                    + "\n~~~"
                )
            results.append(record)
        pages[page] = "\n\n".join(content) + "\n"
        suite = {"external-zpl": "external-zpl", "layout-accuracy": "layout-accuracy"}.get(CORPUS.name, "conformance")
        canonical = REPO / case_page(suite, name)
        pages[canonical] = rebase_links(pages[page], page, canonical)
        if number % 50 == 0:
            print(
                f"Verified artifacts for {number}/{len(cases)} feature fixtures",
                flush=True,
            )
    for lib in LIBRARIES:
        library_rows = []
        for record in results:
            if record["library"] != lib:
                continue
            name = record["case"]
            score = (
                "Unscored"
                if record["score"] is None
                else f"{record['score'] * 100:.2f}% IoU"
            )
            difference = (
                f"[![{NAMES[lib]} difference](../previews/{name}-{lib}-diff.png)](../images/{name}-{lib}-diff.png)"
                if "diff" in record
                else "Unavailable: " + record["status"]
                if "image" not in record
                else "No printer reference"
            )
            library_rows.append(
                [f"[{name}](../cases/{name}.md#{lib})", score, difference]
            )
        pages[DEST / "libraries" / f"{lib}.md"] = (
            "\n\n".join(
                [
                    f"# {NAMES[lib]} versus printer previews",
                    "[All fixtures](../README.md)",
                    legend,
                    table(["Test", "Result", "Difference"], library_rows),
                ]
            )
            + "\n"
        )
    summary = []
    for lib in LIBRARIES:
        scores = [
            r["score"]
            for r in results
            if r["library"] == lib and r["score"] is not None
        ]
        summary.append(
            [
                f"[{NAMES[lib]}](libraries/{lib}.md)",
                len(scores),
                f"{statistics.mean(scores) * 100:.2f}%" if scores else "N/A",
            ]
        )
    summary.sort(
        key=lambda row: float(row[2].rstrip("%")) if row[2] != "N/A" else -1,
        reverse=True,
    )
    capture_end = reference.get("cases", [{}])[-1].get(
        "captured_utc", reference.get("captured_utc", "N/A")
    )
    content = [
        "# "
        + (
            "External example accuracy comparisons"
            if CORPUS.name == "external-zpl"
            else "Font-free layout accuracy comparisons"
            if CORPUS.name == "layout-accuracy"
            else "Feature accuracy comparisons"
        ),
        "[All accuracy comparisons](../../README.md) · [Compatibility features](../../../../compatibility/features/README.md)",
        f"{len(cases)} fixtures × {len(LIBRARIES)} renderers. Execution: {data['measured_utc']}. Printer: {reference.get('device', 'not captured')}, firmware {reference.get('firmware', 'N/A')}, captured {reference.get('captured_utc', 'N/A')} through {capture_end}.",
        f"{len(refs)} hash-matched printer previews; {len(failures)} unavailable previews. Invalid inputs run offline only. "
        + ("Labelary (SaaS) is a renderer, scored against the printer like every other library."
           if "labelary" in LIBRARIES else "Seven local renderers; Labelary captures are not available for this corpus."),
        f"Image coverage: {sum('image' in r for r in results)} successful renders; {sum('diff' in r for r in results)} printer differences. {sum(not c['capture_eligible'] for c in cases)} fixtures are excluded from printer submission. Every successful render with a captured reference has a difference; errors have diagnostics instead of fabricated images.",
        legend,
        "This feature corpus shares the accuracy pipeline and gallery. Its aggregate is separate from the argument/barcode chart because the corpora have different sampling and overlapping command coverage.",
        table(["Library", "Scored cases", "Mean IoU"], summary),
    ]
    content.insert(
        3,
        f"[Capture metadata]({os.path.relpath(reference_path, DEST)})"
        if reference
        else "**Printer references pending.** Renders are available, but correctness scores and differences require a completed, stable printer capture. Incomplete captures are never used as a baseline.",
    )
    comparisons = {(row["case"], row["library"]): row for row in results}
    for group in sorted({c["group"] for c in cases}):
        content += [
            "## " + group,
            table(
                ["Compare renders and diffs", "Classification", "Purpose", *[f"[{NAMES[lib]} IoU](libraries/{lib}.md)" for lib in LIBRARIES]],
                [
                    [
                        f"[{c['name']}](cases/{c['name']}.md)",
                        c["validity"],
                        c["purpose"],
                        *[format_score(comparisons[c["name"], lib]) for lib in LIBRARIES],
                    ]
                    for c in cases
                    if c["group"] == group
                ],
            ),
        ]
    pages[DEST / "README.md"] = "\n\n".join(content) + "\n"
    output = dict(
        schema=1,
        measured_utc=data["measured_utc"],
        inputs={
            str(p.relative_to(REPO)): sha(p)
            for p in [CORPUS / "manifest.json", RENDERS / "results.json"]
            + ([reference_path] if reference else [])
        },
        coverage=dict(
            cases=len(cases),
            attempts=len(results),
            printer_references=len(refs),
            printer_unavailable=len(failures),
            printer_excluded=sum(not c["capture_eligible"] for c in cases),
            rendered_images=sum("image" in r for r in results),
            difference_images=sum("diff" in r for r in results),
        ),
        results=results,
    )
    pages[DEST / "results.json"] = json.dumps(output, indent=2) + "\n"
    for path, text in pages.items():
        text = (
            "<!-- Generated by benchmarks/accuracy/features.py. -->\n\n"
            if path.suffix == ".md"
            else ""
        ) + text
        if check:
            if not path.exists() or path.read_text() != text:
                raise ValueError("Out of date: " + str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    print(
        f"{'Checked' if check else 'Generated'} {len(cases)} feature comparisons and {len(results)} results",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--suite", choices=["features", "external", "layout"], default="features")
    args = parser.parse_args()
    if args.suite == "external":
        CORPUS = REPO / "test-data/external-zpl"
        RENDERS = REPO / "docs/benchmarks/external-zpl"
        REFERENCES = REPO / "benchmarks/accuracy/external-reference"
        DEST = REPO / "docs/benchmarks/accuracy/comparisons/external"
    elif args.suite == "layout":
        CORPUS = REPO / "test-data/layout-accuracy"
        RENDERS = REPO / "docs/benchmarks/layout-accuracy"
        REFERENCES = REPO / "benchmarks/accuracy/layout-reference"
        DEST = REPO / "docs/benchmarks/accuracy/comparisons/layout"
    generate(args.check)
