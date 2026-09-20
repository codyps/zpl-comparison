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
import urllib.error
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
    ap.add_argument(
        "--resume",
        action="store_true",
        help="Resume an incomplete capture, verifying saved hashes and printer identity",
    )
    ap.add_argument(
        "--skip",
        action="append",
        default=[],
        metavar="NAME",
        help="Record a fixture as unavailable without submitting it (requires --skip-reason)",
    )
    ap.add_argument("--skip-reason")
    ap.add_argument(
        "--extend",
        action="store_true",
        help="Add unchanged/new corpus cases to a complete capture and repeat its control",
    )
    ap.add_argument(
        "--object-name",
        default="CMPACC",
        help="Dedicated RAM object; avoid other preview clients' names",
    )
    ap.add_argument(
        "--interval", type=float, default=2, help="Seconds between fixtures"
    )
    ap.add_argument(
        "--cooldown",
        type=float,
        default=30,
        help="Seconds between recovery checks after timeout",
    )
    ap.add_argument(
        "--recovery-attempts",
        type=int,
        default=4,
        help="Maximum spaced recovery checks before stopping resumably",
    )
    args = ap.parse_args()
    if (
        not re.fullmatch(r"[A-Za-z0-9_]{1,8}", args.object_name)
        or args.interval < 0
        or args.cooldown <= 0
        or args.recovery_attempts < 1
    ):
        ap.error(
            "Use a 1-8 character RAM object name and nonnegative interval/positive cooldown"
        )
    if args.extend:
        if not args.corpus:
            ap.error("--extend requires --corpus")
        args.resume = True
    if args.skip and not args.skip_reason:
        ap.error("--skip requires --skip-reason")
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

    def fetch(path, data=None):
        with opener.open(
            urllib.request.Request(urllib.parse.urljoin(base, path), data=data),
            timeout=30,
        ) as response:
            body = response.read(LIMIT + 1)
            if len(body) > LIMIT:
                raise ValueError("Response too large")
            return body

    class PreviewTimeout(ValueError):
        pass

    def request(path, data=None):
        try:
            return fetch(path, data)
        except urllib.error.HTTPError:
            raise
        except (TimeoutError, urllib.error.URLError) as error:
            # Do not immediately replay a POST that may still be executing.
            for attempt in range(args.recovery_attempts):
                print(
                    f"Printer timeout; cooling down {args.cooldown:g}s before recovery check {attempt + 1}/{args.recovery_attempts}",
                    flush=True,
                )
                time.sleep(args.cooldown)
                try:
                    fetch("/")
                except (TimeoutError, urllib.error.URLError):
                    continue
                if data is None:
                    return fetch(path)
                raise PreviewTimeout(
                    "Preview timed out; printer recovered after cooldown; request not replayed"
                ) from error
            raise TimeoutError(
                "Printer unavailable after recovery checks; capture remains resumable"
            ) from error

    home = request("/").decode(errors="replace")
    config = request("/config.html").decode(errors="replace")
    model = re.search(r"ZTC [^<\r\n]+", home)
    firmware = re.search(r"(V[0-9.]+[A-Z]?)\s*(?:&lt;-)?\s+FIRMWARE", config)
    if not model or not firmware or "203dpi" not in model.group():
        raise ValueError("Could not independently identify model/firmware")
    args.output.mkdir(parents=True, exist_ok=args.resume)
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
        "failures": [],
    }
    # Rendering defaults can survive format boundaries on hardware. Reset only
    # content layout properties in a separate preview before each corpus sample.
    reset = b"^XA^PMN^PA0,0,0,0^FPH,0^CVN^BY2,3,100^CI27^CF0,32,0^FWN^LH0,0^LS0^LT0^PON^LRN^XZ"
    manifest["preview_reset_zpl"] = reset.decode()
    if args.corpus:
        manifest["corpus_sha256"] = sha((args.corpus / "manifest.json").read_bytes())

    if set(args.skip) - {p["name"] for p in selected} or set(args.skip) & {
        selected[0]["name"],
        "repeat-end",
    }:
        ap.error("Skip only selected non-control fixtures")
    if args.resume:
        saved = json.loads((args.output / "manifest.json").read_text())
        if args.extend:
            if saved["status"] != "complete" or not saved.get("repeat_pixels_equal"):
                raise ValueError(
                    "Extend only complete, stable captures; use --resume for interrupted extensions"
                )
        elif saved["status"] != "incomplete":
            raise ValueError("Resume only incomplete captures")
        for key in ("device", "firmware", "host", "corpus_sha256", "preview_reset_zpl"):
            if key == "corpus_sha256" and args.extend:
                continue
            if saved.get(key) != manifest.get(key):
                raise ValueError("Capture identity changed: " + key)
        sources = {probe["name"]: sha(probe["zpl"]) for probe in selected}
        for row in saved["cases"] + saved.get("failures", []):
            if sources.get(row["name"]) != row["zpl_sha256"]:
                raise ValueError(
                    "Existing capture source changed or disappeared: " + row["name"]
                )
            if (
                sha((args.output / (row["name"] + ".zpl")).read_bytes())
                != row["zpl_sha256"]
            ):
                raise ValueError("Changed saved source")
            if (
                "png_sha256" in row
                and sha((args.output / (row["name"] + ".png")).read_bytes())
                != row["png_sha256"]
            ):
                raise ValueError("Changed saved preview")
        if args.extend:
            saved.setdefault("corpus_history", []).append(saved["corpus_sha256"])
            saved["corpus_sha256"] = manifest["corpus_sha256"]
            saved["cases"] = [r for r in saved["cases"] if r["name"] != "repeat-end"]
            saved.update(status="incomplete", repeat_pixels_equal=False)
        manifest = saved
        manifest.setdefault("resumed_utc", []).append(
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
    completed = {r["name"] for r in manifest["cases"] + manifest.get("failures", [])}

    def save():
        (args.output / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n"
        )

    save()
    for i, probe in enumerate(selected):
        source = probe.pop("zpl")
        if probe["name"] in completed:
            continue
        skip_reason = args.skip_reason if probe["name"] in args.skip else None
        if b"\x00" in source:
            skip_reason = "Literal NUL bytes omitted from HTTP preview after a binary raster preview stalled the shared printer"
        if skip_reason:
            if probe["name"] in (selected[0]["name"], "repeat-end"):
                raise ValueError("Control cannot contain literal NUL bytes")
            (args.output / f"{probe['name']}.zpl").write_bytes(source)
            manifest["failures"].append(
                {**probe, "zpl_sha256": sha(source), "error": skip_reason}
            )
            save()
            continue
        time.sleep(args.interval)
        if not source.startswith(b"^XA"):
            raise ValueError("Inline reset requires a standard ^XA format")
        # One format/request prevents another client entering between a reset
        # preview and the fixture. The original corpus bytes remain on disk.
        canvas = (
            f"^PW{probe['width']}^LL{probe['height']}".encode()
            if "width" in probe and "height" in probe
            else b""
        )
        submitted = source[:3] + canvas + reset[3:-3] + source[3:]
        probe.update(
            submission_mode="inline-reset-canvas" if canvas else "inline-reset",
            object_name=args.object_name,
            submitted_sha256=sha(submitted),
            captured_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        form = urllib.parse.urlencode(
            {
                "dev": "R",
                "oname": args.object_name,
                "otype": "ZPL",
                "username": "",
                "pw": "",
                "data": submitted,
                "prev": "Preview Label",
            }
        ).encode()
        print(
            f"{i + 1}/{len(selected)} {probe['name']}: requesting preview", flush=True
        )
        try:
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
        except TimeoutError as error:
            # Persist a failed non-control submission before stopping so resume
            # never sends the same problematic fixture again by default.
            if probe["name"] not in (selected[0]["name"], "repeat-end"):
                (args.output / f"{probe['name']}.zpl").write_bytes(source)
                manifest["failures"].append(
                    {**probe, "zpl_sha256": sha(source), "error": str(error)}
                )
                save()
            raise
        except (urllib.error.HTTPError, ValueError) as error:
            if probe["name"] in (selected[0]["name"], "repeat-end"):
                raise
            (args.output / f"{probe['name']}.zpl").write_bytes(source)
            manifest["failures"].append(
                {**probe, "zpl_sha256": sha(source), "error": str(error)}
            )
            save()
            print(i + 1, probe["name"], "unavailable:", error, flush=True)
            continue
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
