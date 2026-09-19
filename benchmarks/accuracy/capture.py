#!/usr/bin/env python3
"""Explicit, preview-only printer capture; offline accuracy runs never use the network.
Protocol matches zebra-http-api/src/lib.rs (form prev=Preview Label, not Print).
"""

import argparse
import hashlib
import html
import io
import importlib.util
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
from PIL import Image
from cases import probes

LIMIT = 16 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def corpus_probes(directory, groups=None):
    """Only hash-verified content fixtures; invalid inputs never reach a printer."""
    directory = directory.resolve()
    spec = importlib.util.spec_from_file_location(
        "content_scope",
        Path(__file__).resolve().parents[2]
        / "test-data/render-conformance/generate.py",
    )
    scope = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scope)
    manifest = json.loads((directory / "manifest.json").read_text())
    selected = []
    for row in manifest["cases"]:
        path = (directory / row["file"]).resolve()
        if not path.is_relative_to(directory):
            raise ValueError("Case path escapes corpus")
        source = path.read_bytes()
        if sha(source) != row["sha256"]:
            raise ValueError("Corpus hash mismatch")
        if row["validity"] == "invalid" or not row["capture_eligible"]:
            continue
        if groups and row["group"] not in groups:
            continue
        if (
            not re.fullmatch(r"[a-zA-Z0-9_.-]+", row["name"])
            or row["name"] == "repeat-end"
        ):
            raise ValueError("Invalid case name")
        scope.commands(source)
        selected.append(
            dict(
                name=row["name"],
                group=row["group"],
                command=" ".join(row["commands"]),
                arguments=row["purpose"],
                width=row["width"],
                height=row["height"],
                zpl=source,
            )
        )
    if not selected:
        raise ValueError("No capture-eligible cases selected")
    selected.append({**selected[0], "name": "repeat-end", "group": "repeatability"})
    return selected


class SameOrigin(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl)[:2] != urllib.parse.urlsplit(req.full_url)[:2]:
            raise ValueError("Cross-origin redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument(
        "--corpus", type=Path, help="Rendering conformance corpus directory"
    )
    ap.add_argument(
        "--group", action="append", help="Select corpus groups (repeatable)"
    )
    args = ap.parse_args()
    if args.group and not args.corpus:
        ap.error("--group requires --corpus")
    selected = corpus_probes(args.corpus, args.group) if args.corpus else probes()
    url = urllib.parse.urlsplit(args.host)
    if (
        url.scheme not in ["http", "https"]
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        ap.error("Use a credential-free printer origin")
    base = urllib.parse.urlunsplit((url.scheme, url.netloc, "/", "", ""))
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), SameOrigin())

    def request(path, data=None):
        with opener.open(
            urllib.request.Request(urllib.parse.urljoin(base, path), data=data),
            timeout=30,
        ) as response:
            body = response.read(LIMIT + 1)
            if len(body) > LIMIT:
                raise ValueError("Response too large")
            return body

    home = request("/").decode(errors="replace")
    config = request("/config.html").decode(errors="replace")
    model = re.search(r"ZTC [^<\r\n]+", home)
    firmware = re.search(r"(V[0-9.]+[A-Z]?)\s*(?:&lt;-)?\s+FIRMWARE", config)
    if not model or not firmware or "203dpi" not in model.group():
        raise ValueError("Could not independently identify model/firmware")
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": 1,
        "status": "incomplete",
        "device": model.group(),
        "firmware": firmware.group(1),
        "dpi": 203,
        "host": base,
        "captured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": "printer HTTP Preview Label; not physical print/scan",
        "cases": [],
    }
    # Rendering defaults can survive format boundaries on hardware. Reset only
    # content layout properties in a separate preview before each corpus sample.
    reset = b"^XA^PMN^PA0,0,0,0^FPH,0^CVN^BY2,3,100^CI27^CF0,32,0^FWN^LH0,0^LS0^LT0^PON^LRN^XZ"
    manifest["preview_reset_zpl"] = reset.decode()
    if args.corpus:
        manifest["corpus_sha256"] = sha((args.corpus / "manifest.json").read_bytes())

    def save():
        (args.output / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n"
        )

    save()
    for i, probe in enumerate(selected):
        source = probe.pop("zpl")
        request(
            "/zpl",
            urllib.parse.urlencode(
                {
                    "dev": "R",
                    "oname": "TEST1",
                    "otype": "ZPL",
                    "username": "",
                    "pw": "",
                    "data": reset,
                    "prev": "Preview Label",
                }
            ).encode(),
        )
        form = urllib.parse.urlencode(
            {
                "dev": "R",
                "oname": "TEST1",
                "otype": "ZPL",
                "username": "",
                "pw": "",
                "data": source,
                "prev": "Preview Label",
            }
        ).encode()
        page = request("/zpl", form).decode(errors="replace")
        match = re.search(r'<IMG\s+SRC="([^"]+)"', page, re.I)
        if not match:
            raise ValueError(f"No preview image for {probe['name']}")
        image_url = urllib.parse.urljoin(base, html.unescape(match.group(1)))
        if urllib.parse.urlsplit(image_url)[:2] != url[:2]:
            raise ValueError("Cross-origin image")
        png = request(image_url)
        with Image.open(io.BytesIO(png)) as image:
            image.load()
            if image.format != "PNG":
                raise ValueError("Not PNG")
            size = image.size
        name = probe["name"]
        (args.output / f"{name}.zpl").write_bytes(source)
        (args.output / f"{name}.png").write_bytes(png)
        probe.update(
            zpl_sha256=sha(source), png_sha256=sha(png), printer_dimensions=list(size)
        )
        manifest["cases"].append(probe)
        save()
        print(i + 1, name, size, flush=True)
    first = (args.output / (manifest["cases"][0]["name"] + ".png")).read_bytes()
    last = (args.output / "repeat-end.png").read_bytes()
    a = Image.open(io.BytesIO(first)).convert("RGBA")
    b = Image.open(io.BytesIO(last)).convert("RGBA")
    manifest["repeat_pixels_equal"] = a.size == b.size and a.tobytes() == b.tobytes()
    manifest["status"] = "complete" if manifest["repeat_pixels_equal"] else "unstable"
    save()
    if manifest["status"] != "complete":
        raise SystemExit("Repeated control changed; capture invalidated")


if __name__ == "__main__":
    main()
