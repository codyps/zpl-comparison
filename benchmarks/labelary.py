#!/usr/bin/env python3
"""Capture Labelary explicitly; regenerate and verify comparison pages offline."""

import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import json
import hashlib
from pathlib import Path
import subprocess
import tempfile
import time


REPO = Path(__file__).resolve().parent.parent
DEFAULT = REPO / "docs/benchmarks/labelary"
SERVICE = "https://labelary.com/service.html"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def inputs():
    from accuracy.run import corpus
    from conformance import load_cases

    cases = []
    accuracy, _, _ = corpus()
    for c in accuracy:
        cases.append(
            dict(
                suite="accuracy",
                name=c["id"],
                source=str(c["zpl"].relative_to(REPO)),
                sha256=c["zpl_sha256"],
                width=c["width"],
                height=c["height"],
                validity="valid",
                printer=str(c["reference"].relative_to(REPO)),
                printer_sha256=c["png_sha256"],
            )
        )
    for suite, folder in [
        ("conformance", "render-conformance"),
        ("external-zpl", "external-zpl"),
        ("layout-accuracy", "layout-accuracy"),
    ]:
        _, rows = load_cases(REPO / "test-data" / folder, invalid=True)
        for c in rows:
            cases.append(
                dict(
                    suite=suite,
                    name=c["name"],
                    source=str(c["path"].relative_to(REPO)),
                    sha256=c["sha256"],
                    width=c["width"],
                    height=c["height"],
                    validity=c["validity"],
                )
            )
    return cases


def key(case):
    return case["suite"] + "--" + case["name"]


def inches(dots):
    # Labelary truncates pixel dimensions; round upward, never below the target dot.
    return str(
        (Decimal(dots) / 203).quantize(Decimal("0.000001"), rounding=ROUND_CEILING)
    )


def capture(dest, extend=False):
    from accuracy.run import gray

    manifest_path = dest / "captures.json"
    if manifest_path.exists() and not extend:
        raise ValueError(
            "Capture already exists; use a new --output directory to preserve its provenance"
        )
    (dest / "images").mkdir(parents=True, exist_ok=True)
    data = dict(
        schema=1,
        service=SERVICE,
        started_utc=now(),
        completed_utc=None,
        renderer_version=None,
        identity="UTC capture timestamps; no renderer version exposed",
        dpmm=8,
        dimension_conversion="inches = ceil(dots / 203 to six decimal places); avoids truncation below the requested dot",
        label_index=0,
        status="incomplete",
        cases=[],
    )
    cases = inputs()
    if extend:
        data = json.loads(manifest_path.read_text())
        expected = {key(c): c for c in cases}
        seen = set()
        for row in data["cases"]:
            if key(row) in seen or key(row) not in expected:
                raise ValueError("Duplicate/removed existing Labelary case")
            seen.add(key(row))
            if (
                any(row.get(k) != v for k, v in expected[key(row)].items())
                or sha(REPO / row["source"]) != row["sha256"]
            ):
                raise ValueError("Existing Labelary source/metadata changed")
            if (
                row["status"] == "rendered"
                and sha(dest / row["image"]) != row["png_sha256"]
            ):
                raise ValueError("Existing Labelary image changed")
            if row["status"] not in {"rendered", "error"} or (
                row["status"] == "error" and not row.get("diagnostic")
            ):
                raise ValueError("Invalid existing Labelary response")
        data.setdefault("extensions", []).append(
            dict(
                started_utc=now(),
                previous_completed_utc=data.get("completed_utc"),
                existing_cases=len(seen),
            )
        )
        data.update(status="incomplete", completed_utc=None)
        cases = [c for c in cases if key(c) not in seen]
        manifest_path.write_text(json.dumps(data, indent=2) + "\n")
    for i, case in enumerate(cases):
        source = REPO / case["source"]
        if sha(source) != case["sha256"]:
            raise ValueError("Changed input: " + str(source))
        url = f"https://api.labelary.com/v1/printers/8dpmm/labels/{inches(case['width'])}x{inches(case['height'])}/0/"
        row = dict(case, requested_utc=now(), url=url)
        with tempfile.TemporaryDirectory() as tmp:
            headers, body = Path(tmp) / "headers", Path(tmp) / "body"
            for attempt in range(5):
                time.sleep(
                    0.55
                )  # Below the public service's three requests/second limit.
                result = subprocess.run(
                    [
                        "curl",
                        "--silent",
                        "--show-error",
                        "--max-time",
                        "45",
                        "--dump-header",
                        str(headers),
                        "--output",
                        str(body),
                        "--write-out",
                        "%{http_code}",
                        "--header",
                        "Accept: image/png",
                        "--header",
                        "Content-Type: application/x-www-form-urlencoded",
                        "--data-binary",
                        "@" + str(source),
                        url,
                    ],
                    capture_output=True,
                    text=True,
                )
                response_headers = {}
                if headers.exists():
                    for line in headers.read_text().splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            k = k.lower().strip()
                            if (
                                k
                                in {
                                    "date",
                                    "server",
                                    "content-type",
                                    "x-total-count",
                                    "x-warnings",
                                    "retry-after",
                                }
                                or "version" in k
                            ):
                                response_headers[k] = v.strip()
                code = int(result.stdout or "0")
                if code not in {429, 502, 503, 504} and result.returncode == 0:
                    break
                if attempt < 4:
                    delay = response_headers.get("retry-after", "5")
                    time.sleep(min(60, max(1, int(delay))) if delay.isdigit() else 5)
            row.update(
                received_utc=now(),
                http_status=code,
                headers=response_headers,
                attempts=attempt + 1,
            )
            version = response_headers.get(
                "x-labelary-version"
            ) or response_headers.get("x-renderer-version")
            row["renderer_version"] = version
            if code == 200 and result.returncode == 0:
                raster = gray(
                    body
                )  # Fully decode before accepting a response as an image.
                image = "images/" + key(case) + ".png"
                (dest / image).write_bytes(
                    body.read_bytes()
                )  # Preserve exact service bytes.
                row.update(
                    status="rendered",
                    image=image,
                    png_sha256=sha(dest / image),
                    dimensions=[raster.shape[1], raster.shape[0]],
                )
            else:
                row.update(
                    status="error",
                    diagnostic=(
                        body.read_text(errors="replace")
                        if body.exists()
                        else result.stderr
                    )[:4000],
                )
        data["cases"].append(row)
        manifest_path.write_text(json.dumps(data, indent=2) + "\n")
        print(f"{i + 1}/{len(cases)} {key(case)} HTTP {code}", flush=True)
    data.update(completed_utc=now(), status="complete")
    manifest_path.write_text(json.dumps(data, indent=2) + "\n")


def validate(dest):
    from accuracy.run import gray

    data = json.loads((dest / "captures.json").read_text())
    expected = {key(c): c for c in inputs()}
    if (
        data["status"] != "complete"
        or len(data["cases"]) != len(expected)
        or {key(c) for c in data["cases"]} != set(expected)
    ):
        raise ValueError("Incomplete capture matrix")
    for case in data["cases"]:
        for field, value in expected[key(case)].items():
            if case[field] != value:
                raise ValueError("Changed case metadata: " + key(case))
        if sha(REPO / case["source"]) != case["sha256"]:
            raise ValueError("Changed source: " + key(case))
        if case["status"] == "rendered":
            image = dest / case["image"]
            if sha(image) != case["png_sha256"]:
                raise ValueError("Changed Labelary image: " + key(case))
            raster = gray(image)
            if case["dimensions"] != [raster.shape[1], raster.shape[0]]:
                raise ValueError("Changed Labelary dimensions: " + key(case))
        elif case["status"] != "error" or not case.get("diagnostic"):
            raise ValueError("Missing response or error diagnostic")
    return data


def register(config):
    """Use saved service responses for renderer comparisons, never performance."""
    import sys

    config["commands"]["labelary"] = [
        sys.executable,
        str(REPO / "benchmarks/adapters/labelary.py"),
    ]


def saved_response(source, width, height, dest=DEFAULT):
    data = json.loads((dest / "captures.json").read_text())
    if data["status"] != "complete":
        raise ValueError("Incomplete Labelary capture")
    digest = sha(source)
    relative = str(source.resolve().relative_to(REPO.resolve()))
    matches = [
        c
        for c in data["cases"]
        if c["source"] == relative
        and c["sha256"] == digest
        and c["width"] == width
        and c["height"] == height
    ]
    if len(matches) != 1:
        raise ValueError(
            "No unique Labelary capture matching source bytes and dimensions"
        )
    case = matches[0]
    if case["status"] != "rendered":
        raise ValueError(f"Labelary HTTP {case['http_status']}: {case['diagnostic']}")
    image = dest / case["image"]
    if sha(image) != case["png_sha256"]:
        raise ValueError("Changed Labelary image")
    return image


def artifacts(dest):
    from report import table

    data = validate(dest)
    versions = sorted(
        {c["renderer_version"] for c in data["cases"] if c["renderer_version"]}
    )
    identity = (
        ", ".join(versions)
        if versions
        else "not exposed; identified by UTC capture timestamps"
    )
    rows = [
        [
            c["suite"],
            c["name"],
            f"[PNG]({c['image']})"
            if c["status"] == "rendered"
            else f"HTTP {c['http_status']}",
        ]
        for c in data["cases"]
    ]
    return {
        "README.md": "\n".join(
            [
                "# Labelary renderer captures\n",
                f"[Service documentation]({SERVICE}). Captured **{data['started_utc']}** through **{data['completed_utc']}**. Renderer version: {identity}.\n",
                "Labelary is an additional renderer. The ZD621 printer captures remain the accuracy baseline. [Printer accuracy scores](../accuracy/README.md) · [Comparison gallery](../accuracy/comparisons/libraries/labelary.md).\n",
                "Exact response PNGs and SHA-256 hashes are retained in [captures.json](captures.json), together with per-request UTC timestamps, dimensions, HTTP status and available response headers. API v1 and the nginx server version are not renderer build versions. No live calls occur in offline tests or CI.\n",
                "Requests use 8 dpmm and label index 0. Dimensions are converted using 203 dots/inch, matching the documented 4-inch = 812-dot example, rounded upward to six decimal places to avoid losing a dot to truncation. Actual response dimensions are recorded without resizing or alignment. Failed responses remain errors; they never fall back to a different renderer.\n",
                table(["Suite", "Case", "Response"], rows),
            ]
        )
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    parser.add_argument(
        "--capture",
        action="store_true",
        help="send corpus bytes to Labelary; requires a new output directory",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify saved captures and generated reports offline",
    )
    parser.add_argument(
        "--extend",
        action="store_true",
        help="Capture only added cases, preserving existing source/image bytes and timestamps",
    )
    args = parser.parse_args()
    if args.extend:
        args.capture = True
    if args.capture and args.check:
        parser.error("--capture and --check are mutually exclusive")
    if args.capture:
        capture(args.output, extend=args.extend)
    generated = artifacts(args.output)
    for name, content in generated.items():
        path = args.output / name
        if args.check:
            if not path.exists() or path.read_text() != content:
                raise ValueError("Stale report: " + str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    print(
        f"{'Verified' if args.check else 'Generated'} {len(generated)} offline comparison artifacts"
    )


if __name__ == "__main__":
    main()
