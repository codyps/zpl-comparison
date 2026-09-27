#!/usr/bin/env python3
"""Prepare, capture and report a narrow ZQ610+/ZD621 comparison campaign.

Uses Pillow for raster inspection; the sibling zpl checkout supplies the native
renderer and preview transport. No physical printing or object downloads.
"""
import argparse
from pathlib import Path
import importlib.util
import io
import html
import json
import re
import subprocess
import socket
import time
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
ZPL = ROOT.parent / "zpl"
TOOL_SOURCE = Path(__file__).read_bytes()
spec = importlib.util.spec_from_file_location("capture", ZPL / "scripts/capture-printer-previews.py")
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)
sha, now, save = capture.sha, capture.now, capture.save


def ink(image):
    return image.convert("L").point(lambda p: 255 if p < 128 else 0)


def measure(image):
    mask = ink(image)
    return {"dimensions": list(image.size), "bbox": mask.getbbox(),
            "ink": mask.histogram()[255]}


def render(data, directory, profile=None):
    source, output = directory / "render.zpl", directory / "render.png"
    source.write_bytes(data)
    cmd = [str(ZPL / "target/debug/examples/zpl-to-svg"), str(source), str(output)]
    if profile:
        cmd += ["--profile", profile]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        with Image.open(output) as image:
            return image.copy()
    finally:
        source.unlink(missing_ok=True)
        output.unlink(missing_ok=True)


def controls():
    for width in (120, 300, 384, 400, 832):
        yield f"canvas-width-{width}", f"^PW{width}^FO8,20^GB32,24,3^FS^FO360,60^GB16,16,2^FS"
    for height in (120, 400, 2030):
        yield f"canvas-height-{height}", f"^LL{height}^FO20,20^GB30,20,3^FS^FO20,500^GB20,20,2^FS"
    for command, args in (("GB", "120,60,3"), ("GC", "61,3"), ("GE", "100,61,3"), ("GD", "120,60,3,B,R")):
        yield "shape-" + command, f"^FO20,40^{command}{args}^FS"
    for font in "0ADE":
        for rotation, origin in (("N", "20,40"), ("R", "200,40"), ("I", "300,140"), ("B", "80,300")):
            yield f"text-{font}-{rotation}", f"^FO{origin}^A{font}{rotation},28,16^FDAB12 test^FS"
    for command in ("^PON", "^POI", "^PMN", "^PMY", "^LT0", "^LT30", "^LS12"):
        yield "layout-" + command[1:], command + "^FO20,40^GB80,30,3^FS"
    yield "text-block", "^FO20,30^A0N,28,14^FB300,4,0,L,0^FDNarrow printer text wraps across lines for comparison.^FS"
    yield "graphic", "^FO20,30^GFA,8,8,1,FF818181818181FF^FS"


def metrics(reference, candidate):
    if reference.size != candidate.size:
        return {"dimensions_equal": False, "exact": False}
    a, b = ink(reference), ink(candidate)
    under = ImageChops.subtract(a, b).histogram()[255]
    over = ImageChops.subtract(b, a).histogram()[255]
    both = ImageChops.darker(a, b).histogram()[255]
    union = under + over + both
    return {"dimensions_equal": True, "underpaint": under, "overpaint": over,
            "both_black": both, "foreground_iou": both / union if union else None,
            "exact": under == over == 0, "nonblank": union > 0}


def report(out, dest, profile):
    manifest = json.loads((out / "manifest.json").read_text())
    verify(out, manifest)
    dest.mkdir(parents=True, exist_ok=True)
    result = {"manifest_sha256": sha((out / "manifest.json").read_bytes()),
              "profile": profile, "zd621_profile": "zd621-preview (ZD621 base plus width quantum 64 and first-draw width latch)", "cases": {}, "unavailable": {}}
    rows = []
    for name, row in manifest["cases"].items():
        if any(row["status"].get(p, {}).get("status") != "captured" for p in ("zq610", "zd621")):
            result["unavailable"][name] = row["status"]
            rows.append(f'<tr><td>{html.escape(name)}</td><td colspan="4">Unpaired: {html.escape(json.dumps(row["status"]))}</td></tr>')
            continue
        directory = dest / name
        directory.mkdir(exist_ok=True)
        comparisons = {}
        native = {}
        for printer in ("zq610", "zd621"):
            image = Image.open(out / name / f"{printer}.png").convert("L")
            native[printer] = image
            (directory / f"{printer}.png").write_bytes((out / name / f"{printer}.png").read_bytes())
            data = (out / name / f"{printer}.zpl").read_bytes()
            (directory / f"{printer}.zpl").write_bytes(data)
            try:
                local = render(data, directory, profile if printer == "zq610" else "zd621-preview")
                local.save(directory / f"{printer}-local.png")
                metric = metrics(image, local)
                metric["local_pixels_sha256"] = sha(local.convert("L").tobytes())
                saved_local = out / name / f"{printer}-local.png"
                saved_local.write_bytes((directory / f"{printer}-local.png").read_bytes())
                metric["local_png_sha256"] = sha(saved_local.read_bytes())
                if metric["dimensions_equal"]:
                    a, b = ink(image), ink(local)
                    diff = Image.new("RGB", image.size, "white")
                    diff.paste((64, 64, 64), mask=ImageChops.darker(a, b))
                    diff.paste((255, 0, 255), mask=ImageChops.subtract(a, b))
                    diff.paste((0, 180, 255), mask=ImageChops.subtract(b, a))
                    diff.save(directory / f"{printer}-diff.png")
                comparisons[printer] = metric
            except subprocess.CalledProcessError as error:
                comparisons[printer] = {"error": error.stderr.decode(), "exact": False}
        # Explicit common-coordinate diagnostic, NOT a full-canvas accuracy gate.
        width = min(native["zq610"].width, native["zd621"].width)
        height = min(native["zq610"].height, native["zd621"].height)
        region = (0, 0, width, height)
        comparisons["common_coordinate_region"] = {"region": region, **metrics(native["zq610"].crop(region), native["zd621"].crop(region))}
        comparisons["capture"] = row
        result["cases"][name] = comparisons
        panels = "".join(f'<figure><figcaption>{p}: native / local / diff</figcaption><div class="panels">' + "".join(f'<a href="{p}{suffix}.png"><img src="{p}{suffix}.png" alt="{p}{suffix}"></a>' for suffix in ("", "-local", "-diff") if (directory / f"{p}{suffix}.png").exists()) + f'</div><a href="{p}.zpl">Submitted ZPL</a></figure>' for p in ("zq610", "zd621"))
        page = f'<h1>{html.escape(name)}</h1><p><a href="../index.html">All comparisons</a></p><p>{html.escape("; ".join(row["changes"]))}</p>{panels}<pre>{html.escape(json.dumps(comparisons, indent=2))}</pre>'
        (directory / "index.html").write_text(document(page))
        rows.append(f'<tr><td><a href="{name}/index.html">{name}</a></td><td>{comparisons["zq610"].get("exact")}</td><td>{comparisons["zd621"].get("exact")}</td><td>{comparisons["common_coordinate_region"]["exact"]}</td><td>{html.escape("; ".join(row["changes"]))}</td></tr>')
    result["summary"] = {key: sum(r[key].get("exact", False) for r in result["cases"].values()) for key in ("zq610", "zd621", "common_coordinate_region")}
    result["summary"]["paired_cases"] = len(result["cases"])
    result["summary"]["unavailable_cases"] = len(result["unavailable"])
    save(dest / "results.json", result)
    save(out / "analysis.json", result)
    body = '<h1>ZQ610 Plus and ZD621 native preview comparisons</h1><p>Native PNGs are unchanged. Local accuracy uses the full native canvas at its original origin, without padding, alignment or resizing. Cross-printer comparison is explicitly limited to the common coordinate region; differing canvas sizes prevent full-image parity.</p><p>Magenta: printer-only ink. Cyan: local-only ink. Dark gray: shared ink. Open images for full native resolution. Deliberate canvas/edge diagnostics can clip; barcode replacements are checked separately for fit. This is a focused campaign, not the full 5,106-record inventory.</p><pre>' + html.escape(json.dumps({"printers": manifest["printers"], "summary": result["summary"], "sessions": manifest["sessions"]}, indent=2)) + '</pre><table><tr><th>Case</th><th>ZQ610 local exact</th><th>ZD621 local exact</th><th>Common-region exact</th><th>Layout changes</th></tr>' + ''.join(rows) + '</table>'
    (dest / "index.html").write_text(document(body))
    (dest / "README.md").write_text('# ZQ610 Plus comparisons\n\n[Open the comparison gallery](index.html).\n\n' + json.dumps(result["summary"], indent=2) + '\n\nSee `references/zq610-plus-v1/manifest.json` for raw capture provenance.\n')
    print(json.dumps(result["summary"]))


def document(body):
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ZQ610 Plus comparison</title><style>body{font:16px system-ui;margin:2rem;max-width:1200px}table{border-collapse:collapse}td,th{padding:.5rem;border:1px solid #bbb;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere}.panels{display:flex;gap:1rem;max-height:480px;overflow:auto}.panels img{image-rendering:pixelated;max-width:none}figure{margin:1rem 0}</style><body>' + body + '</body></html>'


def export_tests(out, dest, extend=False):
    """Export only actually obtained native frames; never manufacture references."""
    manifest = json.loads((out / "manifest.json").read_text())
    verify(out, manifest)
    dest.mkdir(parents=True, exist_ok=extend)
    if extend:
        for row in (dest / "manifest.tsv").read_text().splitlines()[1:]:
            name, source_hash, png_hash, *_ = row.split("\t")
            if sha((dest / (name + ".zpl")).read_bytes()) != source_hash or sha((dest / (name + ".png")).read_bytes()) != png_hash:
                raise ValueError("existing test baseline changed")
    work = dest / "work"
    work.mkdir()
    rows = ["name\tsource_sha256\tprinter_sha256\tunderpaint\toverpaint\tlocal_pixels_sha256\tprinter_ink"]
    sources = []
    for name, row in manifest["cases"].items():
        if row["status"].get("zq610", {}).get("status") == "captured":
            sources.append((name, out / name / "zq610.zpl", out / name / "zq610.png"))
    smoke = ROOT.parent / "zq610-captures"
    original_manifest = capture.verify(smoke)
    for name, row in original_manifest["cases"].items():
        if row["status"] == "captured":
            sources.append(("smoke-" + Path(name).name, smoke / ("captures/" + name + ".submitted.zpl"), smoke / ("captures/" + name + ".png")))
    for name, source, png in sources:
        data, reference = source.read_bytes(), png.read_bytes()
        local = render(data, work, "zq610-plus").convert("L")
        metric = metrics(Image.open(io.BytesIO(reference)), local)
        if not metric.get("exact") or (not metric.get("nonblank") and not manifest["cases"].get(name, {}).get("diagnostic")):
            raise ValueError(f"not an exact baseline (blank requires explicit diagnostic): {name}: {metric}")
        if extend:
            for suffix, content in ((".zpl", data), (".png", reference)):
                target = dest / (name + suffix)
                if target.exists() and target.read_bytes() != content:
                    raise ValueError(f"would replace existing reference: {target}")
        (dest / (name + ".zpl")).write_bytes(data)
        (dest / (name + ".png")).write_bytes(reference)
        rows.append(f"{name}\t{sha(data)}\t{sha(reference)}\t{metric['underpaint']}\t{metric['overpaint']}\t{sha(local.tobytes())}\t{metric['both_black']}")
    (dest / "manifest.tsv").write_text("\n".join(rows) + "\n")
    (dest / "paired-capture.json").write_bytes((out / "manifest.json").read_bytes())
    (dest / "smoke-capture.json").write_bytes((smoke / "provenance.json").read_bytes())
    # Scratch output is not a printer reference or part of the exported corpus.
    for path in work.iterdir():
        path.unlink()
    work.rmdir()
    print("Exported", len(sources), "exact native frames (blank diagnostics explicitly identified)")


def add_fit_controls(out):
    manifest = json.loads((out / "manifest.json").read_text())
    verify(out, manifest)
    for font in "ADE":
        original = f"text-{font}-I"
        name = original + "-fit"
        if name in manifest["cases"]:
            continue
        directory = out / name
        directory.mkdir()
        for printer in ("zq610", "zd621"):
            data = (out / original / f"{printer}.zpl").read_bytes()
            assert data.count(b"^FO300,140") == 1
            data = data.replace(b"^FO300,140", b"^FO20,140")
            path = f"{name}/{printer}.zpl"
            (out / path).write_bytes(data)
            manifest["files"][path] = sha(data)
        predicted = measure(render((directory / "zd621.zpl").read_bytes(), out / "work"))
        assert predicted["bbox"][2] < 384
        manifest["cases"][name] = {"source": f"{name}/zq610.zpl", "status": {},
                                   "changes": ["Move rotated text origin from x=300 to x=20; preserve font size and payload"],
                                   "original_case": original, "fits_narrow_width": True, "predicted": predicted}
    save(out / "manifest.json", manifest)


def add_width_controls(out):
    manifest = json.loads((out / "manifest.json").read_text())
    verify(out, manifest)
    cases = {}
    for width in (1, 63, 64, 65, 127, 128, 383, 384, 385, 800):
        cases[f"width-boundary-{width}"] = f"^PW{width}^LL200^FO0,20^GB{width+20},10,10^FS^FO{width-1},40^GB4,10,4^FS^FO0,60^GB2,10,2^FS"
    cases["width-late-grow"] = "^PW120^LL200^FO300,20^GB20,20,3^FS^PW384"
    cases["width-late-shrink"] = "^PW384^LL200^FO100,20^GB40,20,3^FS^PW120"
    for name, body in cases.items():
        if name in manifest["cases"]:
            continue
        directory = out / name
        directory.mkdir()
        data = b"^XA" + capture.reset() + body.encode() + b"^XZ"
        for printer in ("zq610", "zd621"):
            path = f"{name}/{printer}.zpl"
            (out / path).write_bytes(data)
            manifest["files"][path] = sha(data)
        manifest["cases"][name] = {"source": f"{name}/zq610.zpl", "status": {},
                                   "changes": ["Independent preview-width rounding/clipping holdout"],
                                   "fits_narrow_width": False, "diagnostic": True}
    save(out / "manifest.json", manifest)



def prepare(out):
    out.mkdir(parents=True, exist_ok=False)
    work = out / "work"
    work.mkdir()
    manifest = {"schema": 1, "created_utc": now(), "method": "HTTP Preview Label",
                "zpl_commit": capture.git(ZPL, "rev-parse", "HEAD").decode().strip(),
                "comparison_commit": capture.git(ROOT, "rev-parse", "HEAD").decode().strip(),
                "files": {}, "cases": {}, "printers": {}, "sessions": []}
    def add(name, source, original=None, changes=None, original_measure=None):
        # The same content, origin, and module sizes are sent to both printers;
        # use native widths so ZD621 preview centering is not mistaken for ink drift.
        source = b"^XA" + capture.reset() + b"^PW384^LL2030" + source + b"^XZ"
        directory = out / name
        directory.mkdir()
        row = {"changes": changes or [], "status": {}, "source": name + "/zq610.zpl"}
        if original:
            row["original"] = str(original.relative_to(ZPL))
            row["original_sha256"] = sha(original.read_bytes())
            row["original_measure"] = original_measure
        for printer, data in (("zq610", source), ("zd621", source.replace(b"^PW384", b"^PW832", 1))):
            path = f"{name}/{printer}.zpl"
            (out / path).write_bytes(data)
            manifest["files"][path] = sha(data)
        preview = render(source.replace(b"^PW384", b"^PW832", 1), work)
        row["predicted"] = measure(preview)
        row["fits_narrow_width"] = not row["predicted"]["bbox"] or row["predicted"]["bbox"][2] < 384
        manifest["cases"][name] = row
    for path in sorted((ZPL / "zebra-http-api/tests/fixtures/barcodes-zd621-v1").glob("*.zpl")):
        original = path.read_bytes().strip()
        original_measure = measure(Image.open(path.with_suffix(".png")))
        body = original[3:-3].replace(b"^PW832", b"").replace(b"^LL1218", b"")
        changes = []
        bbox = measure(render(original, work))["bbox"]
        if bbox and bbox[2] >= 384:
            body = body.replace(b"^FO60,60", b"^FO20,60")
            changes.append("Move field from x=60 to x=20")
            probe = render(b"^XA^PW832^LL2030" + body + b"^XZ", work)
            if measure(probe)["bbox"][2] >= 384:
                body = body.replace(b"^BY2,2,80", b"^BY1,2,80")
                body = re.sub(rb"(\^BRN,\d+),2", rb"\1,1", body)
                body = body.replace(b"^BTN,2,2,80,2,4", b"^BTN,1,2,80,1,4")
                changes.append("Reduce barcode horizontal module width from 2 to 1 dot")
        add("barcode-" + path.stem, body, path, changes, original_measure)
    for name, body in controls():
        add(name, body.encode())
    save(out / "manifest.json", manifest)
    print("Prepared", len(manifest["cases"]), "cases")
    print("Predicted clipping:", [n for n, r in manifest["cases"].items() if not r["fits_narrow_width"]])


def verify(out, manifest):
    for path, digest in manifest["files"].items():
        if sha((out / path).read_bytes()) != digest:
            raise ValueError(f"hash mismatch: {path}")


def run_capture(out, args):
    manifest = json.loads((out / "manifest.json").read_text())
    verify(out, manifest)
    def store(path, data):
        (out / path).parent.mkdir(parents=True, exist_ok=True)
        (out / path).write_bytes(data)
        manifest["files"][path] = sha(data)
    for label, host in (("zq610", args.zq610), ("zd621", args.zd621)):
        if args.printer != "both" and label != args.printer:
            continue
        printer = capture.Printer(host)
        home = printer.fetch("/")
        config = printer.fetch("config.html") if label == "zd621" else home
        if label == "zq610":
            identity = capture.identity(home)
        else:
            identity = {"model": re.search(rb"ZTC [^<\r\n]+", home)[0].decode(),
                        "serial": re.search(rb"<H2>([^<]+)</H2>", home)[1].decode(),
                        "firmware": re.search(rb"(V[0-9.]+[A-Z]?)\s*(?:&lt;-)?\s+FIRMWARE", config)[1].decode(), "dpi": 203}
        identity["host"] = host
        if label in manifest["printers"] and identity != manifest["printers"][label]:
            raise ValueError("printer identity changed")
        if ("ZQ610 Plus" if label == "zq610" else "ZD621") not in identity["model"]:
            raise ValueError("wrong printer model")
        manifest["printers"][label] = identity
        session = {"printer": label, "started_utc": now(), "tool_sha256": sha(TOOL_SOURCE)}
        manifest["sessions"].append(session)
        index = len(manifest["sessions"])
        store(f"status/{index}-home.html", home)
        store(f"status/{index}-tool.py", TOOL_SOURCE)
        store(f"status/{index}-config.html", config)
        control_source = (out / "shape-GB" / f"{label}.zpl").read_bytes()
        def control(suffix):
            page, url, png = printer.preview(control_source)
            store(f"status/{index}-{suffix}.zpl", control_source)
            store(f"status/{index}-{suffix}.html", page)
            store(f"status/{index}-{suffix}.png", png)
            session[suffix + "_utc"] = now()
            return Image.open(io.BytesIO(png)).convert("L")
        before = control("before")
        save(out / "manifest.json", manifest)
        completed = 0
        for name, row in sorted(manifest["cases"].items(), key=lambda item: (item[0].startswith("barcode-"), item[0])):
            if args.max_cases is not None and completed >= args.max_cases:
                break
            if name in args.retry_case and row["status"].get(label, {}).get("status") in ("failed", "inflight"):
                row.setdefault("previous_attempts", {}).setdefault(label, []).append(row["status"].pop(label))
            if label in row["status"]:
                continue
            data = (out / name / f"{label}.zpl").read_bytes()
            record = {"status": "inflight", "started_utc": now(), "submitted_sha256": sha(data)}
            row["status"][label] = record
            save(out / "manifest.json", manifest)
            try:
                time.sleep(args.interval)
                page, url, png = printer.preview(data)
                store(f"{name}/{label}.html", page)
                store(f"{name}/{label}.png", png)
                image = Image.open(io.BytesIO(png))
                image.load()
                record.update(status="captured", image_url=url, measurement=measure(image), finished_utc=now())
            except Exception as error:
                record.update(status="failed", error=str(error), finished_utc=now())
                save(out / "manifest.json", manifest)
                raise
            save(out / "manifest.json", manifest)
            print(label, name, record["measurement"], flush=True)
            completed += 1
        after = control("after")
        session["repeat_pixels_equal"] = before.size == after.size and before.tobytes() == after.tobytes()
        session["finished_utc"] = now()
        save(out / "manifest.json", manifest)


def restart(out, host):
    """Explicitly authorized test-printer recovery, never part of capture/retry.

    Zebra: https://support.zebra.com/article/000017569 documents device.reset.
    No language or other configuration-setting commands are sent.
    """
    import urllib.parse
    manifest = json.loads((out / "manifest.json").read_text())
    verify(out, manifest)
    capture.Printer(host)  # Validate the origin before opening its raw port.
    hostname = urllib.parse.urlsplit(host).hostname
    with socket.create_connection((hostname, 9100), timeout=5) as connection:
        connection.settimeout(5)
        connection.sendall(b'! U1 getvar "device.unique_id"\r\n')
        serial = connection.recv(1024).strip().strip(b'"').decode()
    if serial != "XXZMJ230802993":
        raise ValueError("restart printer serial mismatch")
    record = {"requested_utc": now(), "serial": serial, "method": '! U1 do "device.reset" ""', "status": "requested"}
    manifest.setdefault("restarts", []).append(record)
    save(out / "manifest.json", manifest)
    with socket.create_connection((hostname, 9100), timeout=5) as connection:
        connection.sendall(b'! U1 do "device.reset" ""\r\n')
    record["status"] = "sent; recovery must be verified by next HTTP identity check"
    save(out / "manifest.json", manifest)
    print("Sent explicit reset to", serial)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("prepare", "capture", "report", "export-tests", "add-fit-controls", "add-width-controls", "restart"))
    ap.add_argument("--output", type=Path, default=ROOT / "references/zq610-plus-v1")
    ap.add_argument("--zq610", default="http://xxzmj230802993.bed.einic.org/")
    ap.add_argument("--zd621", default="http://d7j211001302.bed.einic.org/")
    ap.add_argument("--interval", type=float, default=0.3)
    ap.add_argument("--printer", choices=("both", "zq610", "zd621"), default="both")
    ap.add_argument("--max-cases", type=int)
    ap.add_argument("--retry-case", action="append", default=[])
    ap.add_argument("--pages", type=Path, default=ROOT / "docs/benchmarks/zq610-plus")
    ap.add_argument("--profile", default=None)
    ap.add_argument("--fixtures", type=Path, default=ZPL / "zpl/tests/fixtures/zq610-plus-v1")
    ap.add_argument("--extend-tests", action="store_true")
    args = ap.parse_args()
    if args.action == "prepare":
        prepare(args.output)
    elif args.action == "capture":
        run_capture(args.output, args)
    elif args.action == "report":
        report(args.output, args.pages, args.profile)
    elif args.action == "export-tests":
        export_tests(args.output, args.fixtures, args.extend_tests)
    elif args.action == "add-fit-controls":
        add_fit_controls(args.output)
    elif args.action == "add-width-controls":
        add_width_controls(args.output)
    else:
        restart(args.output, args.zq610)


if __name__ == "__main__":
    main()
