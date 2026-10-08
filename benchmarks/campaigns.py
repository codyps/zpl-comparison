"""Complete renderer matrices for public documents and paired printer captures."""
import hashlib
import html
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image

from accuracy.metrics import compare
from accuracy.pixels import gray, sha


def matrix(data):
    libraries = data["libraries"]
    cases = [c["name"] for c in data["cases"]]
    keys = [(r["case"], r["library"]) for r in data["results"]]
    if (not libraries or len(set(libraries)) != len(libraries) or len(set(cases)) != len(cases)
            or len(keys) != len(set(keys)) or set(keys) != {(c, lib) for c in cases for lib in libraries}):
        raise ValueError("Incomplete or duplicated campaign renderer matrix")
    return {key: row for key, row in zip(keys, data["results"])}


def assemble(suite, cases, libraries, row_directory, output, **metadata):
    rows = [json.loads(path.read_text()) for path in sorted(Path(row_directory).glob("*.json"))]
    data = dict(schema=2, suite=suite, cases=cases, libraries=libraries, results=rows, **metadata)
    indexed = matrix(data)
    data["results"] = [indexed[(c["name"], lib)] for c in cases for lib in libraries]
    data["measured_utc"] = max((r["observed_utc"] for r in rows if r.get("observed_utc", "")[:4].isdigit()), default="unavailable")
    data["sources"] = json.loads(Path("benchmarks/sources.lock.json").read_text())
    for row in rows:
        if row["status"] not in {"rendered", "blank"}:
            continue
        stem = row["case"] + "-" + row["library"]
        image = output / "images" / (stem + ".png")
        if sha(image) != row["render_sha256"]:
            raise ValueError("Campaign image hash mismatch: " + str(image))
        row.update(image=str(image), png_sha256=row["render_sha256"])
        if "comparison" in row:
            difference = image.with_name(stem + "-diff.png")
            row.update(diff=str(difference), diff_sha256=sha(difference))
    return data


def verify(data, root):
    root = Path(root)
    def path(relative):
        candidate = root / relative
        if not candidate.resolve().is_relative_to(root.resolve()):
            raise ValueError("Campaign evidence escapes report tree")
        return candidate
    indexed = matrix(data)
    for relative, digest in data.get("manifests", {}).items():
        if sha(path(relative)) != digest:
            raise ValueError("Stale campaign manifest: " + relative)
    for case in data["cases"]:
        if sha(path(case["source"])) != case["sha256"] or sha(path(case["reference"])) != case["reference_sha256"]:
            raise ValueError("Changed campaign source/reference: " + case["name"])
        reference = gray(path(case["reference"]))
        for library in data["libraries"]:
            row = indexed[(case["name"], library)]
            if row["source_sha256"] != case["sha256"]:
                raise ValueError("Wrong campaign renderer source")
            if row["status"] not in {"rendered", "blank"}:
                if row.get("image") or row.get("diff") or "comparison" in row or row.get("score") is not None or not row.get("diagnostic"):
                    raise ValueError("Invalid campaign failure evidence")
                continue
            image = path(row["image"])
            if sha(image) != row["png_sha256"]:
                raise ValueError("Changed campaign render")
            actual = gray(image)
            if hashlib.sha256(actual.tobytes()).hexdigest() != row["pixel_sha256"]:
                raise ValueError("Changed campaign pixels")
            if actual.shape != reference.shape:
                if row.get("comparison_status") != "canvas_mismatch" or "comparison" in row or row.get("score") is not None:
                    raise ValueError("Mismatched campaign canvas was scored")
                continue
            metrics, difference = compare(reference, actual)
            expected_score = metrics["iou"] if metrics["reference_ink"] else None
            if row.get("comparison") != metrics or row.get("score") != expected_score or sha(path(row["diff"])) != row["diff_sha256"]:
                raise ValueError("Changed campaign comparison")
            with Image.open(path(row["diff"])) as saved:
                if not np.array_equal(np.asarray(saved.convert("RGB")), difference):
                    raise ValueError("Changed campaign difference pixels")


def reports(data, output, root):
    indexed = matrix(data)
    def link(relative):
        return os.path.relpath(Path(root) / relative, output)
    title = "Public documents against the ZD621" if data["suite"] == "public-zpl" else "Paired ZQ610 Plus / ZD621 comparisons"
    method = (f"{len(data['cases'])} inputs × {len(data['libraries'])} renderers. "
              "Original fixture sources and complete native printer canvases; threshold 128, "
              "without alignment, padding, cropping or resizing. Failures, missing observations "
              "and mismatched canvases remain visible and unscored. Labelary responses are saved "
              "service observations. The printer is the reference. Magenta is printer-only ink; "
              "cyan is renderer-only ink. Barcode decoding does not establish pixel parity.")
    md = ["# " + title, method, "[Gallery](index.html) · [Raw observations](results.json)",
          "| Case | Renderer | Status | Foreground IoU | Underpaint | Overpaint |",
          "| --- | --- | --- | ---: | ---: | ---: |"]
    cards = []
    for case in data["cases"]:
        name = case["name"]
        panels = [f'<h2 id="{html.escape(name)}">{html.escape(name)}</h2>',
                  f'<a href="{html.escape(link(case["source"]))}">Fixture input</a>',
                  f'<p>{html.escape(case.get("notes", ""))}</p>']
        for library in data["libraries"]:
            row = indexed[(name, library)]
            status = row.get("comparison_status", row["status"])
            score = f"{row['score']:.3%}" if row.get("score") is not None else "unscored"
            metrics = row.get("comparison", {})
            md.append(f"| [{name}](index.html#{name}) | {library} | {status} | {score} | {metrics.get('missing', '—')} | {metrics.get('extra', '—')} |")
            panels.append(f'<h3>{html.escape(library)} · {html.escape(status)} · {score}</h3>')
            if row.get("diagnostic"):
                panels.append('<pre>' + html.escape(row["diagnostic"]) + '</pre>')
            pictures = [(case["reference"], "Printer"), (row.get("image"), library), (row.get("diff"), "Difference")]
            panels.append('<div class="panels">' + ''.join(
                f'<figure><figcaption>{html.escape(label)}</figcaption><a href="{html.escape(link(p))}"><img loading="lazy" src="{html.escape(link(p))}" alt="{html.escape(label)}"></a></figure>'
                for p, label in pictures if p) + '</div>')
        cards.append('<article>' + ''.join(panels) + '</article>')
    page = ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>' + title + '</title><style>body{font:16px system-ui;margin:2rem}pre{white-space:pre-wrap}.panels{display:flex;overflow:auto;gap:1rem}figure{margin:0}img{max-width:28vw;image-rendering:pixelated}article{border-top:1px solid #aaa}</style><body><h1>'
            + title + '</h1><p>' + method + '</p><a href="results.json">Raw observations</a>' + ''.join(cards) + '</body></html>\n')
    return {"README.md": "\n\n".join(md[:3]) + "\n\n" + "\n".join(md[3:]) + "\n", "index.html": page}


def write(data, output):
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(data, indent=2) + "\n")
    for name, content in reports(data, output, Path.cwd()).items():
        (output / name).write_text(content)
