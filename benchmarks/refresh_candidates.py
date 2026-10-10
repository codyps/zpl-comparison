"""Refresh selected local adapters while preserving every other saved observation."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import platform
from pathlib import Path
import shutil
import time
import tempfile

from build.compare import comparison
from build.render import render
from benchmarks.accuracy.pixels import sha

ROOT = Path(__file__).resolve().parents[1]
SUITES = ["accuracy", "conformance", "layout-accuracy", "external-zpl", "zq610-candidates"]
CORPORA = {"conformance": "render-conformance", "layout-accuracy": "layout-accuracy", "external-zpl": "external-zpl"}
REFERENCES = {"conformance": "conformance-reference", "layout-accuracy": "layout-reference", "external-zpl": "external-reference"}


def refresh(suite, libraries, work, save=False, jobs=2, library_root=None):
    library_root = library_root or ROOT / "bazel-bin"
    mobile = suite == "zq610-candidates"
    folder = ROOT / ("references/zq610-candidates/saved" if mobile else "docs/benchmarks/" + suite)
    destination = folder / "results.json"
    data = json.loads(destination.read_text())
    references = {}
    if suite in REFERENCES:
        reference_dir = ROOT / "benchmarks/accuracy" / REFERENCES[suite]
        references = {c["name"]: c for c in json.loads((reference_dir / "manifest.json").read_text())["cases"]}
    cases = {c.get("id", c["name"]): c for c in data["cases"]}
    identities = {lib: json.loads((library_root / ("library_" + lib) / "identity.json").read_text()) for lib in libraries}
    identity_hashes = {lib: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest() for lib, value in identities.items()}
    work = work / suite
    work.mkdir(parents=True, exist_ok=True)

    def execute(old):
        cid, lib = old["case"], old["library"]
        case = cases[cid]
        name = cid + "-" + lib
        source = ROOT / (case["source"] if mobile else case["zpl"] if suite == "accuracy" else "test-data/" + CORPORA[suite] + "/" + case["file"])
        digest = case["zpl_sha256"] if suite == "accuracy" else case["sha256"]
        row = dict(case=cid, library=lib, group=case.get("group", "zq610"), score=None)
        if "validity" in case:
            row["validity"] = case["validity"]
        if case.get("reference_unscored_reason"):
            row["comparison_diagnostic"] = case["reference_unscored_reason"]
        if mobile:
            row.update(source_sha256=digest, reference_sha256=case["png_sha256"],
                       requested_dimensions=[case["width"], case["height"]],
                       profile="ZQ610_PLUS_203_DPI; exact source and native requested canvas" if lib in ["codyps-zpl", "codyps-zpl-node", "codyps-zpl-go"] else "pinned library defaults; exact source and native requested canvas")
        spec = dict(source=str(source), sha256=digest, width=case["width"], height=case["height"],
                    library=str(library_root / ("library_" + lib)), row=row, timeout=45)
        if mobile and lib in ["codyps-zpl", "codyps-zpl-node", "codyps-zpl-go"]:
            spec["render_profile"] = "zq610-plus-203dpi"
        metadata, images = work / (name + ".render.json"), work / (name + ".render")
        render(spec, metadata, images)
        reference, reference_hash = None, None
        if suite == "accuracy" or mobile:
            reference, reference_hash = ROOT / case["reference"], case["png_sha256"]
        elif cid in references and case["validity"] != "invalid" and not case.get("reference_unscored_reason"):
            reference, reference_hash = reference_dir / (cid + ".png"), references[cid]["png_sha256"]
        result = work / (name + ".comparison.json")
        comparison(dict(suite="zq610" if mobile else suite, row=str(metadata), image=str(images),
                        reference=str(reference) if reference else None, sha256=reference_hash,
                        strict_native_canvas=mobile), result, work / (name + ".diff"))
        row = json.loads(result.read_text())
        row["adapter_identity_sha256"] = identity_hashes[lib]
        return row

    selected = [r for r in data["results"] if r["library"] in libraries]
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        rows = list(pool.map(execute, selected))
    replacements = {(r["case"], r["library"]): r for r in rows}
    if len(replacements) != len(selected):
        raise ValueError("Duplicate observation")
    from collections import Counter
    print(suite, {lib: dict(Counter(r["status"] for r in rows if r["library"] == lib)) for lib in libraries}, flush=True)
    if not save:
        return rows
    for row in rows:
        name = row["case"] + "-" + row["library"]
        dest = folder / "images" / (name + ".png")
        if row["status"] in ("rendered", "blank"):
            source = work / (name + ".render/image.png")
            if sha(source) != row["render_sha256"]:
                raise ValueError("Changed render: " + name)
            shutil.copyfile(source, dest)
        else:
            dest.unlink(missing_ok=True)
    data["results"] = [replacements.get((r["case"], r["library"]), r) for r in data["results"]]
    data.setdefault("adapters", {}).update(identities)
    data.setdefault("refreshes", []).append(dict(measured_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        host=platform.platform(), libraries=libraries, cases=list(cases), source_lock=json.loads((ROOT / "benchmarks/sources.lock.json").read_text())))
    if mobile:
        data["source_lock"] = json.loads((ROOT / "benchmarks/sources.lock.json").read_text())
    destination.write_text(json.dumps(data, indent=2, sort_keys=mobile) + "\n")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--libraries", required=True, help="Comma-separated built local adapters")
    parser.add_argument("--suites", default=",".join(SUITES))
    parser.add_argument("--work", type=Path, default=ROOT / "benchmarks/_work/failure-refresh")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    suites, libraries = args.suites.split(","), args.libraries.split(",")
    if any(suite not in SUITES for suite in suites):
        parser.error("Unknown suite")
    args.work.mkdir(parents=True, exist_ok=True)
    # Bazel can replace its output trees during another invocation. A verified
    # private copy keeps a long refresh on one immutable adapter artifact.
    with tempfile.TemporaryDirectory(prefix="adapters-", dir=args.work) as temporary:
        library_root = Path(temporary)
        for library in libraries:
            destination = library_root / ("library_" + library)
            shutil.copytree(ROOT / "bazel-bin" / ("library_" + library), destination)
            for item in json.loads((destination / "identity.json").read_text()):
                if sha(destination / item["name"]) != item["sha256"]:
                    raise ValueError("Adapter changed while snapshotting: " + library)
        for suite in suites:
            refresh(suite, libraries, args.work, args.save, args.jobs, library_root)


if __name__ == "__main__":
    main()
