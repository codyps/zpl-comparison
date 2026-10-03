"""Normalize historical observations or export a verified CI observation bundle.

Bundles contain data only. Source definitions and external captures stay in Git.
"""

import argparse
import hashlib
import gzip
import json
from pathlib import Path
import shutil
import tarfile
import tempfile

SUITES = {name: "docs/benchmarks/" + name for name in
          ["accuracy", "conformance", "external-zpl", "layout-accuracy", "zq610-candidates"]}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True) + "\n")


def safe(root, relative):
    path = root / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Unsafe bundle path: " + relative)
    return path


def campaign(source, output, data, suite, revision):
    """Export each campaign renderer independently, including unavailable rows."""
    for original in data["results"]:
        row = dict(original, baseline_revision=revision)
        row.setdefault("observed_utc", data["measured_utc"])
        key = row["case"] + "-" + row["library"]
        if row["status"] in {"rendered", "blank"}:
            image = safe(source, row.get("image", "docs/public-examples/images/" + row["case"] + ".png"))
            recorded = row.get("render_sha256", row.get("png_sha256"))
            if sha(image) != recorded:
                raise ValueError("Campaign observation image hash mismatch")
            row["render_sha256"] = recorded
            target = output / "images" / suite / (key + ".png")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(image, target)
        write(output / "rows" / suite / (key + ".json"), row)


def normalize(source, output, revision):
    source, output = Path(source), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (source / "bundle.json").exists():
        manifest = json.loads((source / "bundle.json").read_text())
        if manifest["schema"] != 1:
            raise ValueError("Unsupported observation bundle")
        if manifest["revision"] != revision:
            raise ValueError("Bundle revision differs from replay lock")
        for relative, digest in manifest["files"].items():
            path = safe(source, relative)
            if not path.is_file() or sha(path) != digest:
                raise ValueError("Bundle hash mismatch: " + relative)
            target = safe(output, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        shutil.copyfile(source / "bundle.json", output / "bundle.json")
        return
    for suite, directory in SUITES.items():
        folder = source / directory
        if suite == "zq610-candidates" and not (folder / "results.json").exists():
            folder = source / "references/zq610-candidates/saved"
        data = json.loads((folder / "results.json").read_text())
        write(output / "metadata" / (suite + ".json"), {k: v for k, v in data.items() if k not in {"results", "adapters"}})
        cases = {c.get("id", c.get("name")): c for c in data["cases"]}
        for observation in data["results"]:
            row = dict(observation)
            case = cases[row["case"]]
            key = row["case"] + "-" + row["library"]
            row.setdefault("source_sha256", case.get("sha256", case.get("zpl_sha256")))
            row.setdefault("requested_dimensions", [case["width"], case["height"]])
            row.setdefault("render_profile", "zq610-plus-203dpi" if suite == "zq610-candidates" and row["library"] == "codyps-zpl" else "zd621-203dpi")
            row.setdefault("observed_utc", data.get("measured_utc", "unknown"))
            row["baseline_revision"] = revision
            if row["status"] in {"rendered", "blank"}:
                image = folder / "images" / (key + ".png")
                if not image.is_file():
                    raise ValueError("Missing successful baseline image: " + str(image))
                recorded = row.get("render_sha256")
                if recorded and sha(image) != recorded:
                    raise ValueError("Baseline image hash mismatch: " + str(image))
                row["render_sha256"] = sha(image)
                target = output / "images" / suite / image.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(image, target)
            write(output / "rows" / suite / (key + ".json"), row)
    invalid = json.loads((source / "docs/benchmarks/invalid/results.json").read_text())
    for row in invalid["results"]:
        name = "-".join(row[k] for k in ["case", "library", "mode"])
        write(output / "probes" / (name + ".json"), row)
    # Preserve current campaign observations in the same per-case replay format.
    public = json.loads((source / "docs/public-examples/results.json").read_text())
    campaign(source, output, public, "public", revision)
    paired_path = source / "docs/benchmarks/zq610-plus/results.json"
    paired_matrix = json.loads(paired_path.read_text()) if paired_path.exists() else {}
    if paired_matrix.get("schema") == 2:
        campaign(source, output, paired_matrix, "paired", revision)
        paired = {"cases": {}}
    else:
        paired = json.loads((source / "references/zq610-plus-v1/analysis.json").read_text())
    for name, case in paired["cases"].items():
        for printer in ["zq610", "zd621"]:
            metric = case[printer]
            if "observation" not in metric:
                continue  # Legacy campaigns are archived, never relabeled as current.
            row = dict(metric["observation"], baseline_revision=revision)
            key = name + "-" + printer + "-codyps-zpl"
            if row["status"] in {"rendered", "blank"}:
                image = source / "references/zq610-plus-v1" / name / (printer + "-local.png")
                if sha(image) != row["render_sha256"]:
                    raise ValueError("Paired observation image hash mismatch")
                target = output / "images/paired" / (key + ".png")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(image, target)
            write(output / "rows/paired" / (key + ".json"), row)
    accuracy = json.loads((source / "docs/benchmarks/accuracy/results.json").read_text())
    write(output / "adapters.json", accuracy.get("adapters", {}))
    shutil.copyfile(source / "benchmarks/sources.lock.json", output / "sources.lock.json")
    # Other report families retain complete, explicitly dated provenance.
    for relative in ["docs/benchmarks/command-support.json", "docs/benchmarks/invalid/results.json",
                     "docs/public-examples", "references/zq610-plus-v1/analysis.json",
                     "benchmarks/popularity.json"]:
        path = source / relative
        if not path.exists():
            continue
        if path.is_dir():
            shutil.copytree(path, output / "reports" / relative, dirs_exist_ok=True)
        else:
            target = output / "reports" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    for path in (source / "references/zq610-plus-v1").glob("*/*-local.png"):
        target = output / "reports" / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    manifest = dict(schema=1, revision=revision,
                    files={str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*")) if p.is_file()})
    write(output / "bundle.json", manifest)


def export(source, archive, revision):
    with tempfile.TemporaryDirectory(prefix="zpl-bundle-") as temporary:
        output = Path(temporary) / "observations"
        normalize(source, output, revision)
        def metadata(info):
            info.mtime = info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mode = 0o755 if info.isdir() else 0o644
            info.pax_headers = {}
            return info
        with Path(archive).open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as stream:
                stream.add(output, arcname="observations", filter=metadata)
    lock = dict(schema=1, kind="bundle", revision=revision, sha256=sha(archive), strip_prefix="observations")
    write(Path(str(archive) + ".json"), lock)
    return lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()
    if args.export:
        export(args.source, args.output, args.revision)
    else:
        normalize(args.source, args.output, args.revision)


if __name__ == "__main__":
    main()
