"""Publish a complete native-canvas matrix from Bazel comparison actions."""
import hashlib
import html
import json
from pathlib import Path
import shutil

LIBRARIES = ["codyps-zpl", "labelize", "forge", "go", "ffi", "binarykits", "zplr", "labelary"]
BASE = Path("docs/benchmarks/zq610-candidates")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def page(body):
    return '<!doctype html><html lang="en"><meta charset="utf-8"><title>ZQ610 renderer candidates</title><style>body{font:16px system-ui;margin:2rem}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:.4rem}.images{display:flex;gap:1rem;overflow:auto;max-height:480px}img{image-rendering:pixelated}pre{white-space:pre-wrap}</style><body>' + body + '</body></html>'


def generate():
    manifest_path = Path("references/zq610-candidates/manifest.json")
    manifest = json.loads(manifest_path.read_text())
    rows = [json.loads(p.read_text()) for p in sorted(Path("_candidate_rows").glob("*.json"))]
    identities = {p.parent.name: json.loads(p.read_text()) for p in Path("_candidate_libraries").glob("*/identity.json")}
    if not identities:
        identities = json.loads(Path("_candidate_saved.json").read_text()).get("adapters", {})
    for row in rows:
        if row["library"] in identities:
            row["adapter_identity_sha256"] = hashlib.sha256(json.dumps(identities[row["library"]], sort_keys=True).encode()).hexdigest()
    expected = {(c["name"], lib) for c in manifest["cases"] for lib in LIBRARIES}
    lookup = {(r["case"], r["library"]): r for r in rows}
    if len(rows) != len(expected) or set(lookup) != expected:
        raise ValueError("Incomplete or duplicate ZQ610 candidate matrix")
    BASE.mkdir(parents=True, exist_ok=True)
    overview = []
    for case in manifest["cases"]:
        name = case["name"]
        for key, digest in (("source", "sha256"), ("reference", "png_sha256")):
            if sha(Path(case[key])) != case[digest]:
                raise ValueError("Native source/reference hash mismatch: " + name)
        directory = BASE / name
        directory.mkdir(exist_ok=True)
        shutil.copyfile(case["source"], directory / "submitted.zpl")
        shutil.copyfile(case["reference"], directory / "printer.png")
        body = f'<h1>{html.escape(name)}</h1><p><a href="../index.html">All cases</a> · <a href="submitted.zpl">Exact submitted ZPL</a></p>'
        cells = []
        for lib in LIBRARIES:
            row = lookup[name, lib]
            score = row.get("score")
            label = row.get("comparison_status", row["status"])
            if score is not None:
                label += f" · {score:.2%} foreground IoU"
            if row.get("exact"):
                label += " · exact" if row.get("reference_ink") else " · blank diagnostic"
            cells.append('<td>' + html.escape(label) + '</td>')
            body += '<h2>' + lib + '</h2><p>' + html.escape(label) + '</p><div class="images"><a href="printer.png"><img src="printer.png" alt="native printer"></a>'
            filename = name + "-" + lib + ".png"
            image = BASE / "images" / filename
            if row["status"] in ("rendered", "blank"):
                if not image.exists() or sha(image) != row["render_sha256"]:
                    raise ValueError("Candidate render hash mismatch: " + filename)
                for file in (filename, name + "-" + lib + "-diff.png"):
                    if (BASE / "images" / file).exists():
                        body += f'<a href="../images/{file}"><img src="../images/{file}" alt="{lib}"></a>'
            body += '</div><pre>' + html.escape(json.dumps(row, indent=2, sort_keys=True)) + '</pre>'
        (directory / "index.html").write_text(page(body))
        overview.append(f'<tr><th><a href="{name}/index.html">{name}</a></th>' + ''.join(cells) + '</tr>')
    results = dict(manifest_sha256=sha(manifest_path), libraries=LIBRARIES,
                   adapters=identities,
                   source_lock=json.loads(Path("benchmarks/sources.lock.json").read_text()),
                   cases=manifest["cases"], results=rows)
    (BASE / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    intro = '<h1>ZQ610 Plus: all renderer candidates</h1><p>Exact source bytes and native requested dimensions; pinned library defaults. The paired-printer gallery separately measures the current local ZQ610 profile. Differing output dimensions are unscored canvas mismatches: no padding, cropping, resizing or alignment. Blank diagnostics are not positive accuracy evidence. Failed or uncaptured candidates remain visible. Each image opens at native resolution.</p><p><a href="results.json">Results and adapter provenance</a> · <a href="../zq610-plus/index.html">Current local profile and paired printers</a></p>'
    (BASE / "index.html").write_text(page(intro + '<table><tr><th>Case</th>' + ''.join('<th>' + lib + '</th>' for lib in LIBRARIES) + '</tr>' + ''.join(overview) + '</table>'))
    (BASE / "README.md").write_text('# ZQ610 Plus renderer candidates\n\n[Native comparison matrix](index.html) · [Measurements and identities](results.json)\n')


if __name__ == "__main__":
    generate()
