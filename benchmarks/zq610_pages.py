#!/usr/bin/env python3
"""Rebuild ZQ610 comparison pages from saved evidence, without a printer/renderer."""
import hashlib
import html
import json
from pathlib import Path
import shutil
import sys
from PIL import Image, ImageChops


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def page(body):
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ZQ610 Plus comparisons</title><style>body{font:16px system-ui;margin:2rem;max-width:1200px}pre{white-space:pre-wrap;overflow-wrap:anywhere}td,th{border:1px solid #bbb;padding:.5rem}table{border-collapse:collapse}.panels{display:flex;gap:1rem;max-height:480px;overflow:auto}img{image-rendering:pixelated;max-width:none}</style><body>' + body + '</body></html>'


def generate(source, dest):
    source, dest = Path(source), Path(dest)
    manifest = json.loads((source / "manifest.json").read_text())
    analysis = json.loads((source / "analysis.json").read_text())
    if sha(source / "manifest.json") != analysis["manifest_sha256"]:
        raise ValueError("analysis is stale for capture manifest")
    for path, digest in manifest["files"].items():
        if sha(source / path) != digest:
            raise ValueError(f"capture hash mismatch: {path}")
    dest.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, result in analysis["cases"].items():
        directory = dest / name
        directory.mkdir(exist_ok=True)
        panels = []
        for printer in ("zq610", "zd621"):
            for suffix in (".zpl", ".png"):
                shutil.copyfile(source / name / (printer + suffix), directory / (printer + suffix))
            metric = result[printer]
            files = [printer + ".png"]
            local = source / name / (printer + "-local.png")
            if "local_png_sha256" in metric:
                if sha(local) != metric["local_png_sha256"]:
                    raise ValueError(f"local PNG hash mismatch: {local}")
                shutil.copyfile(local, directory / local.name)
                files.append(local.name)
                if metric.get("dimensions_equal"):
                    with Image.open(source / name / (printer + ".png")) as raw, Image.open(local) as rendered:
                        a = raw.convert("L").point(lambda p: 255 if p < 128 else 0)
                        b = rendered.convert("L").point(lambda p: 255 if p < 128 else 0)
                    diff = Image.new("RGB", a.size, "white")
                    diff.paste((64, 64, 64), mask=ImageChops.darker(a, b))
                    diff.paste((255, 0, 255), mask=ImageChops.subtract(a, b))
                    diff.paste((0, 180, 255), mask=ImageChops.subtract(b, a))
                    filename = printer + "-diff.png"
                    diff.save(directory / filename)
                    files.append(filename)
            panels.append(f'<h2>{printer}: native / local / diff</h2><div class="panels">' + ''.join(f'<a href="{f}"><img src="{f}" alt="{f}"></a>' for f in files) + f'</div><a href="{printer}.zpl">Exact submitted ZPL</a>')
        body = f'<h1>{html.escape(name)}</h1><a href="../index.html">All comparisons</a>' + ''.join(panels) + '<pre>' + html.escape(json.dumps(result, indent=2)) + '</pre>'
        (directory / "index.html").write_text(page(body))
        rows.append(f'<tr><td><a href="{name}/index.html">{name}</a></td><td>{result["zq610"].get("exact")}</td><td>{result["zd621"].get("exact")}</td><td>{result["common_coordinate_region"]["exact"]}</td></tr>')
    for name, status in analysis["unavailable"].items():
        rows.append(f'<tr><td>{html.escape(name)}</td><td colspan="3">Unavailable: {html.escape(json.dumps(status))}</td></tr>')
    body = '<h1>ZQ610 Plus / ZD621 previews</h1><p>Full native canvases are compared with local output at their original origin, without padding, resizing, cropping or alignment. Cross-printer equality refers only to the explicitly recorded common coordinate region. Magenta: printer-only ink; cyan: local-only ink. Click images for full resolution.</p><p>Sources and unchanged native PNGs have verified SHA-256 hashes. Missing cases are listed, never synthesized. The focused campaign does not represent the entire 5,106-case inventory. Deliberate edge diagnostics may clip; narrow replacements are separately identified in case metadata.</p><pre>' + html.escape(json.dumps({"printers": manifest["printers"], "summary": analysis["summary"], "sessions": manifest["sessions"]}, indent=2)) + '</pre><table><tr><th>Case</th><th>ZQ610 local exact</th><th>ZD621 local exact</th><th>Common region exact</th></tr>' + ''.join(rows) + '</table>'
    (dest / "index.html").write_text(page(body))
    shutil.copyfile(source / "analysis.json", dest / "results.json")
    (dest / "README.md").write_text('# ZQ610 Plus / ZD621\n\n[Comparison gallery](index.html) · [Raw metrics](results.json)\n\n' + json.dumps(analysis["summary"], indent=2) + '\n')


if __name__ == "__main__":
    generate(sys.argv[1] if len(sys.argv) > 1 else "references/zq610-plus-v1", sys.argv[2] if len(sys.argv) > 2 else "docs/benchmarks/zq610-plus")
