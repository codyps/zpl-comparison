"""Index every ZQ610 case and capture Labelary explicitly outside Bazel actions."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "references/zq610-candidates"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    paired = ROOT / "references/zq610-plus-v1"
    manifest = json.loads((paired / "manifest.json").read_text())
    fixtures = ROOT.parent / "zpl/zpl/tests/fixtures/zq610-plus-v1"
    DEST.mkdir(exist_ok=True)
    cases = []
    for line in (fixtures / "manifest.tsv").read_text().splitlines()[1:]:
        name, source_hash, png_hash, *_ = line.split("\t")
        if name in manifest["cases"]:
            source, image = paired / name / "zq610.zpl", paired / name / "zq610.png"
        else:
            assert name.startswith("smoke-")
            source, image = DEST / (name + ".zpl"), DEST / (name + ".png")
            for dest, suffix in ((source, ".zpl"), (image, ".png")):
                contents = (fixtures / (name + suffix)).read_bytes()
                if dest.exists() and dest.read_bytes() != contents:
                    raise ValueError("Existing smoke evidence differs")
                dest.write_bytes(contents)
        assert sha(source) == source_hash and sha(image) == png_hash
        with Image.open(image) as png:
            width, height = png.size
        cases.append(dict(name=name, source=str(source.relative_to(ROOT)), sha256=source_hash,
                          reference=str(image.relative_to(ROOT)), png_sha256=png_hash,
                          width=width, height=height))
    shutil.copyfile(fixtures / "smoke-capture.json", DEST / "smoke-provenance.json")
    data = dict(cases=cases, printer=manifest["printers"]["zq610"],
                paired_manifest_sha256=sha(paired / "manifest.json"),
                smoke_provenance_sha256=sha(DEST / "smoke-provenance.json"),
                policy="All case outputs, including four original smoke cases; session repeatability captures remain provenance, not duplicate scored cases")
    service = DEST / "labelary/captures.json"
    data["labelary"] = json.loads(service.read_text())["cases"] if service.exists() else []
    (DEST / "manifest.json").write_text(json.dumps(data, indent=2) + "\n")
    saved = DEST / "saved"
    saved.mkdir(exist_ok=True)
    if not (saved / "results.json").exists():
        (saved / "results.json").write_text('{"results": []}\n')


def labelary_capture():
    # Reuse the established bounded HTTP capture and response provenance path.
    import labelary
    manifest = json.loads((DEST / "manifest.json").read_text())
    labelary.inputs = lambda: [dict(c, suite="zq610", validity="valid") for c in manifest["cases"]]
    dest = DEST / "labelary"
    labelary.capture(dest, extend=(dest / "captures.json").exists())
    prepare()


def save_candidates(actions):
    """Preserve actual Bazel outputs for reports_saved, with no fabricated rows."""
    results = actions / "zq610-candidate-pages/docs/benchmarks/zq610-candidates/results.json"
    data = json.loads(results.read_text())
    if data["manifest_sha256"] != sha(DEST / "manifest.json"):
        raise ValueError("Candidate results are stale")
    expected = {(c["name"], lib) for c in data["cases"] for lib in data["libraries"]}
    if {(r["case"], r["library"]) for r in data["results"]} != expected or len(data["results"]) != len(expected):
        raise ValueError("Candidate matrix is incomplete")
    saved = DEST / "saved"
    (saved / "images").mkdir(exist_ok=True)
    for row in data["results"]:
        if row["status"] in ("rendered", "blank"):
            name = row["case"] + "-" + row["library"]
            source = actions / "zq610-candidates" / (name + ".render/image.png")
            if sha(source) != row["render_sha256"]:
                raise ValueError("Candidate image changed: " + name)
            shutil.copyfile(source, saved / "images" / (name + ".png"))
    shutil.copyfile(results, saved / "results.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "labelary", "save-candidates"])
    parser.add_argument("--bazel-actions", type=Path, default=ROOT / "bazel-bin/reports_actions")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "labelary":
        labelary_capture()
    else:
        save_candidates(args.bazel_actions)
