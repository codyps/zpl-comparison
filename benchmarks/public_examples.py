#!/usr/bin/env python3
"""Compare public documents with native ZD621 captures and saved Labelary responses.

No network calls. Capture separately with accuracy/capture.py --corpus
and labelary.py --extend.
The adapter is benchmarks/adapters/rust built against the selected zpl checkout.
"""

import argparse
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
from PIL import Image

from conformance import load_cases, reference_images
from accuracy.pixels import gray, sha
from accuracy.metrics import compare
import labelary

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "test-data/public-zpl"
REFERENCE = ROOT / "references/public-zd621-20261002"
OUTPUT = ROOT / "docs/public-examples"


def verified_inputs():
    spec = importlib.util.spec_from_file_location("public_prepare", CORPUS / "prepare.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, data in module.artifacts().items():
        if (CORPUS / name).read_bytes() != data:
            raise ValueError("Stale public fixture: " + name)
    manifest, cases = load_cases(CORPUS)
    reference, images = reference_images(REFERENCE, cases)
    if reference["corpus_sha256"] != sha(CORPUS / "manifest.json"):
        raise ValueError("Stale capture corpus")
    if set(images) != {case["name"] for case in cases}:
        raise ValueError("Missing public document capture")
    for case in cases:
        if images[case["name"]].shape != (case["height"], case["width"]):
            raise ValueError("Unexpected printer canvas: " + case["name"])
    return manifest, cases, reference, images


def source_identity(source, renderer):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()
    paths = [source / "Cargo.lock", source / "Cargo.toml"]
    for crate in ["zpl", "raster-diff"]:
        paths.append(source / crate / "Cargo.toml")
        for directory in ["src", "assets"]:
            paths.extend(p for p in (source / crate / directory).rglob("*") if p.is_file())
    hashes = {str(p.relative_to(source)): sha(p) for p in sorted(paths)}
    return dict(
        revision=git("rev-parse", "HEAD"), status=git("status", "--porcelain"),
        source_files=hashes,
        source_sha256=hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
        adapter_sha256=sha(renderer),
        adapter_sources={name: sha(ROOT / "benchmarks/adapters/rust/src" / name)
                         for name in ["main.rs", "probe.rs"]},
        profile="zpl::render::profiles::ZD621_203_DPI", dpi=203,
    )


def measure(renderer, source, output, cases, images, reference):
    output.mkdir(parents=True, exist_ok=False)
    (output / "images").mkdir()
    rows = []
    identity = source_identity(source, renderer)
    for case in cases:
        name = case["name"]
        path = output / "images" / f"{name}.png"
        row = dict(case=name, library="codyps-zpl", source_sha256=case["sha256"])
        try:
            proc = subprocess.run(
                [str(renderer), "accuracy", str(case["path"]), "1", str(path),
                 str(case["width"]), str(case["height"])],
                env={**os.environ, "ZPL_RENDER_PROFILE": "zd621-203dpi"},
                capture_output=True, timeout=30, check=False,
            )
            row.update(returncode=proc.returncode, diagnostic=proc.stderr.decode(errors="replace"))
            row["status"] = "error" if proc.returncode else "rendered"
            if proc.returncode:
                path.unlink(missing_ok=True)
            else:
                raster = gray(path)
                row.update(png_sha256=sha(path), pixel_sha256=hashlib.sha256(raster.tobytes()).hexdigest())
                row["status"] = "rendered" if np.any(raster < 128) else "blank"
                if raster.shape != images[name].shape:
                    row.update(comparison_status="canvas_mismatch", output_dimensions=[raster.shape[1], raster.shape[0]])
                else:
                    metrics, diff = compare(images[name], raster)
                    row["comparison"] = metrics
                    Image.fromarray(diff).save(path.with_name(name + "-diff.png"))
                    row["diff_sha256"] = sha(path.with_name(name + "-diff.png"))
        except subprocess.TimeoutExpired:
            path.unlink(missing_ok=True)
            row.update(status="timeout", diagnostic="Adapter exceeded 30 seconds; no retry")
        rows.append(row)
        print(name, row["status"], row.get("comparison", {}).get("iou"), flush=True)
    result = dict(
        schema=1, suite="public-zpl-20261002", measured_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        host=platform.platform(), manifest_sha256=sha(CORPUS / "manifest.json"),
        reference_manifest_sha256=sha(REFERENCE / "manifest.json"),
        renderer=identity, printer={k: reference[k] for k in ["device", "firmware", "dpi", "method"]},
        results=rows,
    )
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def verify(result, output, cases, images):
    if result["manifest_sha256"] != sha(CORPUS / "manifest.json") or result["reference_manifest_sha256"] != sha(REFERENCE / "manifest.json"):
        raise ValueError("Stale measurement inputs")
    if [row["case"] for row in result["results"]] != [case["name"] for case in cases]:
        raise ValueError("Incomplete or duplicated measurements")
    for case, row in zip(cases, result["results"]):
        if row["source_sha256"] != case["sha256"]:
            raise ValueError("Wrong measured source")
        path = output / "images" / (case["name"] + ".png")
        if row["status"] not in {"rendered", "blank"}:
            if path.exists() or "comparison" in row or not row.get("diagnostic"):
                raise ValueError("Invalid failure evidence")
            continue
        if sha(path) != row["png_sha256"]:
            raise ValueError("Changed render")
        raster = gray(path)
        if hashlib.sha256(raster.tobytes()).hexdigest() != row["pixel_sha256"]:
            raise ValueError("Changed rendered pixels")
        if raster.shape != images[case["name"]].shape:
            if row.get("comparison_status") != "canvas_mismatch" or "comparison" in row:
                raise ValueError("Canvas mismatch was scored")
            continue
        metrics, diff = compare(images[case["name"]], raster)
        difference = path.with_name(case["name"] + "-diff.png")
        if metrics != row["comparison"] or sha(difference) != row["diff_sha256"]:
            raise ValueError("Changed comparison")
        if not np.array_equal(np.array(Image.open(difference).convert("RGB")), diff):
            raise ValueError("Difference pixels do not match evidence")
    audit_path = output / "barcodes.json"
    if audit_path.exists():
        for row in json.loads(audit_path.read_text())["results"]:
            path = (ROOT / row["file"]).resolve()
            if not path.is_relative_to(ROOT) or sha(path) != row["png_sha256"]:
                raise ValueError("Changed independent decoder input")


def service_comparisons(output, cases, images, check=False):
    """Replay exact service responses; never align or pad a mismatched canvas."""
    captures = labelary.validate(labelary.DEFAULT)
    captured = [row for row in captures["cases"] if row["suite"] == "public-zpl"]
    by_name = {row["name"]: row for row in captured}
    if len(captured) != len(cases) or set(by_name) != {c["name"] for c in cases}:
        raise ValueError("Incomplete public Labelary captures")
    rows = []
    for case in cases:
        name = case["name"]
        capture = by_name[name]
        row = dict(case=name, library="labelary", source_sha256=capture["sha256"],
                   **{k: capture[k] for k in ["status", "requested_utc", "received_utc",
                                             "url", "http_status", "renderer_version"]})
        if capture["status"] == "error":
            row["diagnostic"] = capture["diagnostic"]
        else:
            path = labelary.DEFAULT / capture["image"]
            raster = gray(path)
            row.update(image=str(path.relative_to(ROOT)), png_sha256=capture["png_sha256"],
                       status="rendered" if np.any(raster < 128) else "blank",
                       output_dimensions=[raster.shape[1], raster.shape[0]])
            if raster.shape != images[name].shape:
                row["comparison_status"] = "canvas_mismatch"
            else:
                metrics, diff = compare(images[name], raster)
                row["comparison"] = metrics
                row["diff"] = f"images/{name}-labelary-diff.png"
                difference = output / row["diff"]
                if check:
                    if not np.array_equal(np.array(Image.open(difference).convert("RGB")), diff):
                        raise ValueError("Changed Labelary difference pixels: " + name)
                else:
                    Image.fromarray(diff).save(difference)
                row["diff_sha256"] = sha(difference)
        rows.append(row)
    return dict(schema=1, suite="public-zpl-20261002", service=captures["service"],
                identity=captures["identity"],
                captures_rows_sha256=hashlib.sha256(json.dumps(captured, sort_keys=True).encode()).hexdigest(),
                manifest_sha256=sha(CORPUS / "manifest.json"),
                reference_manifest_sha256=sha(REFERENCE / "manifest.json"), results=rows)


def reports(result, service, output, cases):
    def link(relative):
        return os.path.relpath(ROOT / relative, output)

    rows = result["results"]
    exact = sum(r.get("comparison", {}).get("exact", False) for r in rows)
    rendered = sum(r["status"] == "rendered" for r in rows)
    summary = f"zpl: {len(cases)} labels, {rendered} rendered, {exact} pixel-exact full canvases, {len(cases) - rendered} render failures."
    identity = result["renderer"]
    intro = (f"{summary} Measured {result['measured_utc']} using zpl {identity['revision']} "
             f"with {identity['profile']}. Printer: {result['printer']['device']}, "
             f"{result['printer']['firmware']}, {result['printer']['dpi']} dpi.")
    service_rows = service["results"]
    service_exact = sum(r.get("comparison", {}).get("exact", False) for r in service_rows)
    service_rendered = sum(r["status"] == "rendered" for r in service_rows)
    intro += (f" Labelary: {service_rendered} rendered, {service_exact} pixel-exact full canvases. "
              f"Captured {min(r['requested_utc'] for r in service_rows)} through "
              f"{max(r['received_utc'] for r in service_rows)}; {service['identity']}.")
    method = ("HTTP Preview Label captures; no physical print/scan. The start/end control matches. "
              "Compare complete native canvases at the original origin, threshold 128; no alignment, "
              "padding, cropping or rescaling. IoU measures foreground intersection/union, not white-background agreement. "
              "Magenta is printer-only ink (underpaint); cyan is renderer-only ink (overpaint). "
              "Whole-label IoU is not a per-text-field score or proof of barcode decoding/symbol parity. "
              "Blank references and unequal canvases are unscored. Labelary is another renderer; the printer remains the reference. "
              "Other libraries were not measured in this campaign.")
    links = (f"[Interactive gallery](index.html) · [Sources, adaptations and reproduction]({link('test-data/public-zpl/README.md')}) · "
             f"[Capture provenance]({link('references/public-zd621-20261002/manifest.json')}) · [zpl results](results.json) · "
             f"[Labelary results](labelary-results.json) · [Service responses]({link('docs/benchmarks/labelary/captures.json')})")
    md = ["# Public examples against the ZD621", intro, links, method,
          "| Document | Renderer | Status | Foreground IoU | Underpaint | Overpaint |\n| --- | --- | --- | ---: | ---: | ---: |"]
    cards = []
    for case, row, service_row in zip(cases, rows, service_rows):
        name = case["name"]
        metrics = row.get("comparison", {})
        status = "exact" if metrics.get("exact") else row.get("comparison_status", row["status"])
        iou = f"{metrics['iou'] * 100:.3f}%" if metrics.get("reference_ink") else "unscored"
        md.append(f"| [{name}](index.html#{name}) | zpl | {status} | {iou} | {metrics.get('missing', '—')} | {metrics.get('extra', '—')} |")
        service_metrics = service_row.get("comparison", {})
        service_status = "exact" if service_metrics.get("exact") else service_row.get("comparison_status", service_row["status"])
        service_iou = f"{service_metrics['iou'] * 100:.3f}%" if service_metrics.get("reference_ink") else "unscored"
        md.append(f"| [{name}](index.html#{name}) | Labelary | {service_status} | {service_iou} | {service_metrics.get('missing', '—')} | {service_metrics.get('extra', '—')} |")
        pictures = [(link(f"references/public-zd621-20261002/{name}.png"), "Printer preview")]
        if row["status"] in {"rendered", "blank"}:
            pictures.append((f"images/{name}.png", "zpl"))
        if metrics:
            pictures.append((f"images/{name}-diff.png", "zpl difference"))
        if service_row.get("image"):
            pictures.append((link(service_row["image"]), "Labelary"))
        if service_row.get("diff"):
            pictures.append((service_row["diff"], "Labelary difference"))
        pictures = "".join(f'<figure><figcaption>{label}</figcaption><a href="{url}"><img src="{url}" alt="{html.escape(name)} — {label}" loading="lazy"></a></figure>' for url, label in pictures)
        diagnostic = f'<pre>{html.escape(row.get("diagnostic", ""))}</pre>' if row.get("diagnostic") else ""
        service_detail = (f'<p>Labelary: {service_status} · foreground IoU {service_iou} · '
                          f'underpaint {service_metrics.get("missing", "—")} · overpaint {service_metrics.get("extra", "—")}</p>')
        if service_row.get("diagnostic"):
            service_detail += f'<pre>{html.escape(service_row["diagnostic"])}</pre>'
        source_link = link("test-data/public-zpl/" + case["file"])
        cards.append(f'<article id="{name}" data-status="{status}"><h2>{html.escape(name)}</h2><p>{html.escape(case["purpose"])}</p><p>zpl: {status} · foreground IoU {iou} · underpaint {metrics.get("missing", "—")} · overpaint {metrics.get("extra", "—")} · {case["width"]} × {case["height"]} dots</p><p><a href="{case["source"]}">Pinned upstream</a> · <a href="{source_link}">Exact input</a></p><p>{html.escape(case["notes"])}</p>{diagnostic}{service_detail}<div class="pictures">{pictures}</div></article>')
    findings = link("docs/public-examples/FINDINGS.md")
    md.append(f"\nSee [findings]({findings}) for source diagnostics and limits.\n")
    page = ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Public ZPL examples — ZD621 comparison</title><style>body{font:16px system-ui;margin:24px;color:#18212a;background:#f6f7f8}article{padding:20px;background:white;margin:24px 0;border:1px solid #ccc}h2{overflow-wrap:anywhere}.pictures{display:flex;gap:20px;overflow:auto}figure{margin:0;flex:0 0 auto}figcaption{font-weight:bold;margin-bottom:8px}img{max-width:28vw;height:auto;border:1px solid #aaa;image-rendering:pixelated}body.native img{max-width:none}pre{white-space:pre-wrap;overflow-wrap:anywhere}button,select{font:inherit;padding:6px}nav{position:sticky;top:0;background:#f6f7f8;padding:12px}a{color:#124f9b}</style>'
            f'<h1>Public ZPL examples against the ZD621</h1><p>{html.escape(intro)}</p><p>{html.escape(method)}</p>'
            f'<p><a href="README.md">Results table</a> · <a href="{findings}">Findings</a></p>'
            '<nav><label>Filter zpl results <select id="filter"><option value="all">All documents</option><option value="differences">Differences and errors</option><option value="exact">Exact matches</option></select></label> <button id="size" aria-pressed="false">Show native pixels</button></nav>'
            + "".join(cards)
            + '<script>document.getElementById("filter").onchange=e=>{for(const a of document.querySelectorAll("article")){a.hidden=e.target.value==="exact"?a.dataset.status!=="exact":e.target.value==="differences"?a.dataset.status==="exact":false}};document.getElementById("size").onclick=e=>{const native=document.body.classList.toggle("native");e.target.setAttribute("aria-pressed",String(native));e.target.textContent=native?"Fit previews":"Show native pixels"}</script></html>\n')
    return {"README.md": "\n\n".join(md[:5]) + "\n" + "\n".join(md[5:]), "index.html": page}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--renderer", type=Path, help="Existing Rust codyps-zpl adapter executable")
    parser.add_argument("--source", type=Path, default=ROOT.parent / "zpl")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true", help="Offline integrity/reproduction check, without executing a renderer")
    parser.add_argument("--reports-only", action="store_true", help="Rebuild reports from saved zpl and Labelary images offline")
    args = parser.parse_args()
    _, cases, reference, images = verified_inputs()
    if args.check or args.reports_only:
        result = json.loads((args.output / "results.json").read_text())
    else:
        if not args.renderer:
            parser.error("--renderer is required unless --check or --reports-only is used")
        result = measure(args.renderer.resolve(), args.source.resolve(), args.output.resolve(), cases, images, reference)
    verify(result, args.output, cases, images)
    service = service_comparisons(args.output, cases, images, check=args.check)
    artifacts = reports(result, service, args.output, cases)
    artifacts["labelary-results.json"] = json.dumps(service, indent=2) + "\n"
    for name, content in artifacts.items():
        path = args.output / name
        if args.check:
            if path.read_text() != content:
                raise ValueError("Stale report: " + name)
        else:
            path.write_text(content)
    print("Verified public sources, captures, renders, native comparisons and reports")


if __name__ == "__main__":
    main()
