#!/usr/bin/env python3
"""Run conformance fixtures through the existing renderer adapters.

No printer traffic. Optional references come from accuracy/capture.py --corpus.
PNG comparison is shared with accuracy/run.py; source cases cite the Zebra guide.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import time
import statistics
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SUITE = REPO / "test-data/render-conformance"
spec = importlib.util.spec_from_file_location(
    "accuracy_metrics", ROOT / "accuracy/run.py"
)
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)
from report import NAMES, table  # noqa: E402


def load_cases(directory=SUITE, groups=None, invalid=False):
    manifest = json.loads((directory / "manifest.json").read_text())
    rows = []
    for case in manifest["cases"]:
        path = (directory / case["file"]).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError("Case path escapes corpus")
        if hashlib.sha256(path.read_bytes()).hexdigest() != case["sha256"]:
            raise ValueError(f"Case hash mismatch: {path}")
        if groups and case["group"] not in groups:
            continue
        if case["validity"] == "invalid" and not invalid:
            continue
        rows.append({**case, "path": path})
    if not rows:
        raise ValueError("No cases selected")
    return manifest, rows


def reference_images(directory, cases):
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest["status"] != "complete" or not manifest["repeat_pixels_equal"]:
        raise ValueError("Incomplete or unstable references")
    lookup = {}
    for row in manifest["cases"]:
        name = row["name"]
        if Path(name).name != name:
            raise ValueError("Invalid reference name")
        if (
            metrics.sha(directory / (name + ".zpl")) != row["zpl_sha256"]
            or metrics.sha(directory / (name + ".png")) != row["png_sha256"]
        ):
            raise ValueError("Reference hash mismatch")
        if row.get("submission_mode") in {"inline-reset", "inline-reset-canvas", "ram-setup-inline-reset-canvas"}:
            source = (directory / (name + ".zpl")).read_bytes()
            reset = manifest["preview_reset_zpl"].encode()
            canvas = (
                f"^PW{row['width']}^LL{row['height']}".encode()
                if row["submission_mode"] != "inline-reset"
                else b""
            )
            ram_setup = row["submission_mode"] == "ram-setup-inline-reset-canvas"
            start = source.rfind(b"^XA") if ram_setup else 0
            if start < 0:
                raise ValueError("Missing format after resource preamble")
            if ram_setup and hashlib.sha256(source[:start]).hexdigest() != row.get("setup_sha256"):
                raise ValueError("RAM setup hash mismatch")
            submitted = (source[start:start + 3] if ram_setup else source[:3]) + canvas + reset[3:-3] + source[start + 3:]
            if (
                not source[start:].startswith(b"^XA")
                or hashlib.sha256(submitted).hexdigest() != row["submitted_sha256"]
            ):
                raise ValueError("Submitted preview hash mismatch")
        elif row.get("submission_mode") is not None:
            raise ValueError("Unknown preview submission mode")
        lookup[name] = row
    first = manifest["cases"][0]["name"]
    if not np.array_equal(
        metrics.gray(directory / (first + ".png")),
        metrics.gray(directory / "repeat-end.png"),
    ):
        raise ValueError("Repeated control changed")
    selected = {}
    for case in cases:
        row = lookup.get(case["name"])
        if case.get("reference_unscored_reason") and not row:
            raise ValueError("Missing diagnostic reference")
        if row:
            if row["zpl_sha256"] != case["sha256"]:
                raise ValueError("Reference belongs to different input")
            if case.get("reference_unscored_reason"):
                continue
            selected[case["name"]] = metrics.gray(directory / (case["name"] + ".png"))
    if not selected:
        raise ValueError("No matching reference cases")
    return manifest, selected


def relations(cases, outcomes, images, libraries):
    groups = defaultdict(list)
    for case in cases:
        if case["relation"]:
            groups[case["relation"]["set"]].append(case["name"])
    result = []
    for library in libraries:
        for group, names in groups.items():
            keys = [(library, n) for n in names]
            # Two failing or blank renderers cannot earn a metamorphic pass.
            if len(keys) < 2 or any(outcomes[k]["status"] != "rendered" for k in keys):
                status = "inconclusive"
            else:
                status = (
                    "equal"
                    if all(
                        np.array_equal(images[keys[0]] < 128, images[k] < 128)
                        for k in keys[1:]
                    )
                    else "different"
                )
            result.append(dict(library=library, set=group, cases=names, status=status))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--only", default="all", help="Comma-separated renderer adapters, or all (default)"
    )
    ap.add_argument("--group", action="append", help="Repeat to select fixture groups")
    ap.add_argument(
        "--corpus",
        type=Path,
        default=SUITE,
        help="Corpus directory containing manifest.json",
    )
    ap.add_argument("--include-invalid", action="store_true")
    ap.add_argument(
        "--reports-only",
        action="store_true",
        help="Regenerate Markdown from saved execution results",
    )
    ap.add_argument("--reference", type=Path)
    ap.add_argument("--output", type=Path, default=ROOT / "_work/conformance")
    ap.add_argument("--timeout", type=float, default=15)
    ap.add_argument(
        "--jobs",
        type=int,
        default=4,
        help="Concurrent offline renders (not timing measurements)",
    )
    args = ap.parse_args()
    if args.jobs < 1:
        ap.error("Jobs must be positive")
    if args.timeout <= 0:
        ap.error("Timeout must be positive")
    manifest, cases = load_cases(
        args.corpus, groups=args.group, invalid=args.include_invalid
    )
    if args.reports_only:
        data = json.loads((args.output / "results.json").read_text())
        report(data, args.output, args.corpus)
        return
    cfg = json.loads((ROOT / "_work/config.json").read_text())
    from labelary import DEFAULT, register, validate

    register(cfg)
    libraries = metrics.LIBRARIES if args.only == "all" else args.only.split(",")
    if (
        not libraries
        or len(set(libraries)) != len(libraries)
        or any(
            n not in metrics.LIBRARIES or n not in cfg["commands"] for n in libraries
        )
    ):
        ap.error("Select built rendering adapters")
    if "labelary" in libraries:
        validate(DEFAULT)
    metrics.preflight(cfg, libraries)
    refs = {}
    reference = None
    if args.reference:
        reference, refs = reference_images(args.reference, cases)
    dest = args.output
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "images").mkdir(exist_ok=True)
    outcomes = {}
    images = {}
    env = {**os.environ, **cfg["environment"]}

    def render(item):
        case, library = item
        key = (library, case["name"])
        path = dest / "images" / f"{case['name']}-{library}.png"
        path.unlink(missing_ok=True)
        result = dict(
            library=library,
            case=case["name"],
            group=case["group"],
            validity=case["validity"],
            score=None,
        )
        command = cfg["commands"][library] + [
            "accuracy",
            str(case["path"]),
            "1",
            str(path),
            str(case["width"]),
            str(case["height"]),
        ]
        try:
            process = subprocess.run(
                command,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=args.timeout,
            )
            result["returncode"] = process.returncode
            result["diagnostic"] = process.stderr.decode(errors="replace")[-1500:]
            if process.returncode:
                result["status"] = "crashed" if process.returncode < 0 else "error"
            else:
                raster = metrics.gray(path)
                if case["relation"]:
                    images[key] = raster
                ink = int(np.count_nonzero(raster < 128))
                result.update(
                    status="rendered" if ink else "blank",
                    ink=ink,
                    width=raster.shape[1],
                    height=raster.shape[0],
                )
                Image.fromarray(raster).save(path, optimize=True)
                if case["name"] in refs and case["validity"] != "invalid":
                    comparison, diff = metrics.compare(refs[case["name"]], raster)
                    result["comparison"] = comparison
                    result["score"] = (
                        comparison["iou"] if comparison["reference_ink"] else None
                    )
                    Image.fromarray(diff).save(
                        path.with_name(path.stem + "-diff.png"), optimize=True
                    )
        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
        except Exception as error:
            result.update(status="error", diagnostic=str(error))
        if (
            case["name"] in refs
            and case["validity"] != "invalid"
            and result["status"] in ["error", "crashed", "timeout"]
            and np.any(refs[case["name"]] < 128)
        ):
            result["score"] = 0.0
        return key, result

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for i, (key, result) in enumerate(
            pool.map(render, ((c, lib) for c in cases for lib in libraries))
        ):
            outcomes[key] = result
            if (i + 1) % len(libraries) == 0:
                print(f"{(i + 1) // len(libraries)}/{len(cases)} {key[1]}", flush=True)
    checks = relations(cases, outcomes, images, libraries)
    result = dict(
        schema=1,
        suite=manifest["suite"],
        manifest_sha256=metrics.sha(args.corpus / "manifest.json"),
        measured_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        host=platform.platform(),
        cases=[{k: v for k, v in case.items() if k != "path"} for case in cases],
        references=reference,
        results=list(outcomes.values()),
        relations=checks,
    )
    (dest / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    report(result, dest, args.corpus)
    if any(r["status"] in ["crashed", "timeout"] for r in outcomes.values()):
        raise SystemExit("Renderer crash/timeout; report preserved")


def report(data, dest, corpus=SUITE):
    manifest, all_cases = load_cases(corpus, invalid=True)
    if data["manifest_sha256"] != metrics.sha(corpus / "manifest.json"):
        raise ValueError("Stale conformance results")
    selected = {c["name"] for c in data["cases"]}
    cases = [c for c in all_cases if c["name"] in selected]
    if [{k: v for k, v in c.items() if k != "path"} for c in cases] != data["cases"]:
        raise ValueError("Stale conformance case metadata")
    libraries = list(dict.fromkeys(r["library"] for r in data["results"]))
    outcomes = {(r["library"], r["case"]): r for r in data["results"]}
    if len(outcomes) != len(data["results"]) or set(outcomes) != {
        (lib, c["name"]) for c in cases for lib in libraries
    }:
        raise ValueError("Incomplete conformance result matrix")
    checks = data["relations"]
    text = [
        "# Rendering conformance run\n",
        "[Feature printer/render/difference gallery](../accuracy/comparisons/features/README.md)\n"
        if corpus.resolve() == SUITE.resolve()
        else "[External printer/render/difference gallery](../accuracy/comparisons/external/README.md)\n"
        if corpus.name == "external-zpl"
        else "[Font-free layout printer/render/difference gallery](../accuracy/comparisons/layout/README.md)\n"
        if corpus.name == "layout-accuracy"
        else "",
        f"Suite: `{manifest['suite']}`. {len(cases)} cases; {len(libraries)} adapters.\n",
        "This reports execution and equal-image relationships, not printer accuracy unless hash-matched printer references were supplied. A rendered image can still be wrong. Font coverage is device-dependent. Invalid inputs are kept separate.\n",
    ]
    if manifest.get("sources"):
        text += [
            "## Imported examples\n",
            "Unmodified upstream inputs, including stateful and printer-configuration examples, run offline only. Boundary classification means unverified example semantics, not certified valid ZPL. Upstream library fixtures are not an independent holdout.\n",
            table(
                ["Fixture", "Group", "Canvas (dots)", "Pinned source"],
                [
                    [
                        f"[{c['name']}]({os.path.relpath(c['path'], dest)})",
                        c["group"],
                        f"{c['width']}×{c['height']}",
                        f"[upstream]({c['source']})",
                    ]
                    for c in cases
                ],
            ),
        ]
    summary = []
    for library in libraries:
        row = [
            r
            for r in outcomes.values()
            if r["library"] == library and r["validity"] != "invalid"
        ]
        scores = [r["score"] for r in row if r["score"] is not None]
        summary.append(
            [
                NAMES[library],
                len(row),
                *[
                    sum(r["status"] == status for r in row)
                    for status in ["rendered", "blank", "error", "crashed", "timeout", "not_captured"]
                ],
                f"{statistics.mean(scores) * 100:.2f}%" if scores else "N/A",
            ]
        )
    text += [
        table(
            [
                "Library",
                "Valid/boundary cases",
                "Nonblank",
                "Blank",
                "Errors",
                "Crashes",
                "Timeouts",
                "Not measured",
                "Printer IoU",
            ],
            summary,
        ),
        "\n## Equal-raster relationships\n",
        "Equality requires at least two nonblank successful outputs. Both blanks/errors are inconclusive; equality alone is not printer fidelity.\n",
        table(
            ["Library", "Relationship", "Outcome"],
            [[r["library"], r["set"], r["status"]] for r in checks],
        ),
        "\n## Individual cases\n",
    ]
    for validity in ["valid", "boundary", "invalid"]:
        tab = []
        for case in cases:
            if case["validity"] != validity:
                continue
            values = []
            for lib in libraries:
                r = outcomes[(lib, case["name"])]
                status = r["status"]
                if status in ["rendered", "blank"]:
                    status = f"[{status}](images/{case['name']}-{lib}.png)"
                if r["score"] is not None:
                    status += f" ({r['score'] * 100:.1f}% IoU)"
                values.append(status)
            case_label = (
                f"[{case['name']}](../accuracy/comparisons/{'features' if corpus.resolve() == SUITE.resolve() else 'layout' if corpus.name == 'layout-accuracy' else 'external'}/cases/{case['name']}.md)"
                if corpus.resolve() == SUITE.resolve() or corpus.name in {"external-zpl", "layout-accuracy"}
                else case["name"]
            )
            tab.append([case_label, *values])
        if tab:
            text.extend(
                [
                    f"### {validity}\n",
                    table(["Case", *[NAMES[n] for n in libraries]], tab),
                ]
            )
    (dest / "README.md").write_text("\n".join(text))


if __name__ == "__main__":
    main()
