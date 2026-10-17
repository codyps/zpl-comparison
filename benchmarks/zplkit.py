"""Collect ZPLKit PNGs on macOS and import verified observations on Linux.

Collection uses only the standard library. Import reuses the comparison engine
and each suite's existing scoring policy; neither stage rewrites fixture ZPL.
"""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import time

LIBRARY = "zplkit"
COMPARISONS = {"conformance": "features", "external-zpl": "external", "layout-accuracy": "layout"}
ADAPTER_FILES = ["benchmarks/adapters/swift/Package.swift",
                 "benchmarks/adapters/swift/Sources/zplkit-adapter/Adapter.swift",
                 "benchmarks/zplkit.py"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def safe(root, relative):
    path = root / relative
    if Path(relative).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Unsafe observation path: " + relative)
    return path


def cases(root):
    """The same fixtures, IDs, canvases and reference eligibility as pipeline.bzl."""
    rows = []

    def add(suite, name, source, width, height, reference=None, **hashes):
        row = dict(suite=suite, case=name, source=source,
                   source_sha256=sha(root / source), requested_dimensions=[width, height])
        if hashes.get("source_sha256", row["source_sha256"]) != row["source_sha256"]:
            raise ValueError("Changed fixture: " + source)
        if reference:
            row.update(reference=reference, reference_sha256=sha(root / reference))
            if hashes.get("reference_sha256", row["reference_sha256"]) != row["reference_sha256"]:
                raise ValueError("Changed printer reference: " + reference)
        rows.append(row)

    fresh = read(root / "benchmarks/accuracy/reference/manifest.json")
    for case in fresh["cases"]:
        if case["group"] != "repeatability":
            base = "benchmarks/accuracy/reference/" + case["name"]
            add("accuracy", "argument-" + case["name"], base + ".zpl", case["width"], case["height"], base + ".png",
                source_sha256=case["zpl_sha256"], reference_sha256=case["png_sha256"])
    archive = read(root / "references/barcodes-zd621-v1/manifest.json")
    for name, case in archive["cases"].items():
        base = "references/barcodes-zd621-v1/" + name
        add("accuracy", "barcode-" + name, base + ".zpl", archive["width"], 1218, base + ".png",
            source_sha256=case["zpl_sha256"], reference_sha256=case["printer_png_sha256"])
    for suite, corpus, ref in [("conformance", "render-conformance", "conformance"),
                              ("external-zpl", "external-zpl", "external"),
                              ("layout-accuracy", "layout-accuracy", "layout")]:
        references = {c["name"]: c for c in read(root / f"benchmarks/accuracy/{ref}-reference/manifest.json")["cases"]}
        for case in read(root / f"test-data/{corpus}/manifest.json")["cases"]:
            reference = f"benchmarks/accuracy/{ref}-reference/{case['name']}.png"
            eligible = case["name"] in references and case["validity"] != "invalid" and not case.get("reference_unscored_reason")
            add(suite, case["name"], f"test-data/{corpus}/{case['file']}", case["width"], case["height"],
                reference if eligible else None, source_sha256=case["sha256"],
                **({"reference_sha256": references[case["name"]]["png_sha256"]} if eligible else {}))
    for case in read(root / "references/zq610-candidates/manifest.json")["cases"]:
        add("zq610-candidates", case["name"], case["source"], case["width"], case["height"], case["reference"],
            source_sha256=case["sha256"], reference_sha256=case["png_sha256"])
    public_refs = {c["name"]: c for c in read(root / "references/public-zd621-20261002/manifest.json")["cases"]}
    for case in read(root / "test-data/public-zpl/manifest.json")["cases"]:
        add("public", case["name"], "test-data/public-zpl/" + case["file"], case["width"], case["height"],
            "references/public-zd621-20261002/" + case["name"] + ".png",
            source_sha256=case["sha256"], reference_sha256=public_refs[case["name"]]["png_sha256"])
    paired = read(root / "references/zq610-plus-v1/manifest.json")
    for name, case in paired["cases"].items():
        if any(case["status"].get(p, {}).get("status") != "captured" for p in ["zq610", "zd621"]):
            continue
        for printer in ["zq610", "zd621"]:
            status = case["status"][printer]
            width, height = status["measurement"]["dimensions"]
            base = "references/zq610-plus-v1/" + name + "/" + printer
            add("paired", name + "-" + printer, base + ".zpl", width, height, base + ".png",
                source_sha256=status["submitted_sha256"],
                reference_sha256=paired["files"][name + "/" + printer + ".png"])
    keys = [(r["suite"], r["case"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate fixture ID")
    return rows


def collect(root, adapter, output, timeout=30):
    if output.exists():
        raise ValueError("Choose a new observation directory")
    pin = read(root / "benchmarks/sources.lock.json")[LIBRARY]
    actual = subprocess.check_output(["git", "-C", str(root / "benchmarks/_work/zplkit"), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(root / "benchmarks/_work/zplkit"), "status", "--porcelain"], text=True).strip()
    if actual != pin["rev"] or dirty:
        raise ValueError("ZPLKit checkout must be clean and match sources.lock.json")
    identity = dict(source=pin, adapter_files={p: sha(root / p) for p in ADAPTER_FILES},
                    binary_sha256=sha(adapter), platform=platform.platform(), machine=platform.machine(),
                    swift=subprocess.check_output(["swift", "--version"], text=True).strip(),
                    xcode=subprocess.check_output(["xcodebuild", "-version"], text=True).strip(),
                    runner_image=os.environ.get("ImageVersion"),
                    ci={k: os.environ.get(k) for k in ["GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_REPOSITORY"]})
    definitions = cases(root)
    output.mkdir(parents=True)
    results = []
    for case in definitions:
        row = dict(case, library=LIBRARY, observed_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        image = output / "images" / case["suite"] / (case["case"] + ".png")
        image.parent.mkdir(parents=True, exist_ok=True)
        command = [str(adapter), "accuracy", str(root / case["source"]), "1", str(image),
                   *map(str, case["requested_dimensions"])]
        try:
            proc = subprocess.run(command, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL)
            row.update(returncode=proc.returncode, diagnostic=proc.stderr.decode(errors="replace")[-1800:],
                       status="crashed" if proc.returncode < 0 else "error" if proc.returncode else "rendered")
        except subprocess.TimeoutExpired:
            row.update(status="timeout", diagnostic="Renderer exceeded its time limit")
        if row["status"] == "rendered":
            if not image.is_file() or not image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("Adapter succeeded without a PNG: " + str(command))
            row.update(image=str(image.relative_to(output)), raw_png_sha256=sha(image))
        else:
            image.unlink(missing_ok=True)
        results.append(row)
        print(case["suite"], case["case"], row["status"], flush=True)
    write(output / "observations.json", dict(schema=1, library=LIBRARY, adapter=identity, results=results))
    if not any(r["status"] == "rendered" for r in results):
        raise ValueError("ZPLKit produced no successful renders")


def verified(root, artifact, definitions):
    data = read(artifact / "observations.json")
    pin = read(root / "benchmarks/sources.lock.json")[LIBRARY]
    if data["schema"] != 1 or data["library"] != LIBRARY or data["adapter"]["source"] != pin:
        raise ValueError("Wrong ZPLKit source identity")
    if data["adapter"]["adapter_files"] != {p: sha(root / p) for p in ADAPTER_FILES}:
        raise ValueError("Stale ZPLKit adapter")
    keys = [(r["suite"], r["case"]) for r in data["results"]]
    if len(keys) != len(set(keys)) or set(keys) != {(c["suite"], c["case"]) for c in definitions}:
        raise ValueError("Incomplete or duplicated ZPLKit observations")
    indexed = dict(zip(keys, data["results"]))
    for case in definitions:
        row = indexed[(case["suite"], case["case"])]
        if any(row.get(k) != v for k, v in case.items()) or row["library"] != LIBRARY:
            raise ValueError("Stale ZPLKit fixture: " + case["case"])
        if row["status"] == "rendered":
            if sha(safe(artifact, row["image"])) != row["raw_png_sha256"]:
                raise ValueError("Changed ZPLKit PNG")
        elif row["status"] not in {"error", "crashed", "timeout"} or row.get("image"):
            raise ValueError("Invalid ZPLKit failure evidence")
    return data, indexed


def merge(root, artifact, reports):
    import numpy as np
    from PIL import Image
    from build.compare import comparison
    from benchmarks.accuracy.pixels import gray

    definitions = cases(root)
    data, indexed = verified(root, artifact, definitions)
    documents = {}
    def document(relative):
        if relative not in documents:
            documents[relative] = read(reports / relative)
            if any(r["library"] == LIBRARY for r in documents[relative]["results"]):
                raise ValueError("ZPLKit already imported: " + relative)
        return documents[relative]

    # Check the entire destination matrix before importing any image.
    for suite in {c["suite"] for c in definitions}:
        relative = result_path(suite)
        doc = document(relative)
        expected = {c["case"] for c in definitions if c["suite"] == suite}
        actual = {c.get("id", c.get("name")) for c in doc["cases"]}
        if expected != actual:
            raise ValueError("Report fixture coverage differs: " + suite)

    identity_hash = hashlib.sha256(json.dumps(data["adapter"], sort_keys=True).encode()).hexdigest()
    for case in definitions:
        suite, name = case["suite"], case["case"]
        source = indexed[(suite, name)]
        row = {k: source[k] for k in ["case", "library", "observed_utc", "source_sha256", "requested_dimensions",
                                      "reference_sha256", "returncode", "diagnostic", "status", "raw_png_sha256"] if k in source}
        row.update(adapter_identity_sha256=identity_hash, adapter=data["adapter"], score=None)
        base = str(Path(result_path(suite)).parent)
        assets = "docs/benchmarks/accuracy/comparisons/" + COMPARISONS[suite] if suite in COMPARISONS else base
        stem = name + "-" + LIBRARY
        image_path = base + "/images/" + stem + ".png"
        with tempfile.TemporaryDirectory(prefix="zplkit-import-") as tmp:
            tmp = Path(tmp)
            raster, diff = tmp / "render", tmp / "difference"
            raster.mkdir()
            if source["status"] == "rendered":
                pixels = gray(safe(artifact, source["image"]))
                Image.fromarray(pixels).save(raster / "image.png", compress_level=1)
                ink = int(np.count_nonzero(pixels < 128))
                row.update(status="rendered" if ink else "blank", ink=ink, width=pixels.shape[1], height=pixels.shape[0],
                           render_sha256=sha(raster / "image.png"), pixel_sha256=hashlib.sha256(pixels.tobytes()).hexdigest())
            write(tmp / "row.json", row)
            spec = dict(suite=suite, row=str(tmp / "row.json"), image=str(raster),
                        strict_native_canvas=suite in {"zq610-candidates", "public", "paired"})
            if case.get("reference"):
                # Check the report copy too: never compare against different evidence.
                reference = safe(reports, case["reference"])
                if sha(reference) != case["reference_sha256"]:
                    raise ValueError("Changed report reference")
                spec.update(reference=str(reference), sha256=case["reference_sha256"])
            comparison(spec, str(tmp / "scored.json"), str(diff))
            scored = read(tmp / "scored.json")
            if source["status"] == "rendered":
                target = reports / image_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(raster / "image.png", target)
                scored.update(image=image_path, png_sha256=sha(target))
            if (diff / "image.png").exists():
                target = reports / assets / "images" / (stem + "-diff.png")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(diff / "image.png", target)
                scored.update(diff=str(target.relative_to(reports)), diff_sha256=sha(target))
            document(result_path(suite))["results"].append(scored if suite not in COMPARISONS else row)
            if suite in COMPARISONS:
                relative = assets + "/results.json"
                document(relative)["results"].append(scored)

    for relative, doc in documents.items():
        # Existing observations keep their dates, host and provenance.
        if "libraries" in doc and isinstance(doc["libraries"], list):
            doc["libraries"].append(LIBRARY)
        if relative == result_path("accuracy"):
            doc.setdefault("adapters", {})[LIBRARY] = data["adapter"]
        if "coverage" in doc:
            coverage = doc["coverage"]
            coverage.update(attempts=len(doc["results"]), rendered_images=sum(r["status"] in {"rendered", "blank"} for r in doc["results"]),
                            difference_images=sum(bool(r.get("diff")) for r in doc["results"]))
        write(reports / relative, doc)
    # Bind comparison evidence to the newly augmented observation documents.
    for suite, comparison_name in COMPARISONS.items():
        relative = "docs/benchmarks/accuracy/comparisons/" + comparison_name + "/results.json"
        doc = documents[relative]
        doc["inputs"][result_path(suite)] = sha(reports / result_path(suite))
        write(reports / relative, doc)
    write(reports / "docs/benchmarks/zplkit/adapter.json", data["adapter"])
    print("Imported ZPLKit observations:", dict(Counter(c["suite"] for c in definitions)))


def result_path(suite):
    return {"public": "docs/public-examples/results.json", "paired": "docs/benchmarks/zq610-plus/results.json"}.get(suite, "docs/benchmarks/" + suite + "/results.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "collect", "merge"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--reports", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.action == "plan":
        definitions = cases(root)
        print(json.dumps(dict(cases=len(definitions), suites=dict(Counter(c["suite"] for c in definitions))), indent=2))
    elif args.action == "collect":
        collect(root, args.adapter.resolve(), args.artifact.resolve())
    else:
        merge(root, args.artifact.resolve(), args.reports.resolve())


if __name__ == "__main__":
    main()
