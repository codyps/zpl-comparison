#!/usr/bin/env python3
"""Compare a fresh preview capture with saved evidence, without alignment or network."""

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rows(manifest):
    cases = manifest["cases"]
    if isinstance(cases, dict):
        return [{"name": name, **row} for name, row in cases.items()]
    return cases


def checked_image(directory, row):
    name = row["name"]
    if Path(name).name != name:
        raise ValueError("Unsafe capture name")
    source = (directory / (name + ".zpl")).read_bytes()
    png = (directory / (name + ".png")).read_bytes()
    expected = row.get("png_sha256", row.get("printer_png_sha256"))
    if sha(source) != row["zpl_sha256"] or sha(png) != expected:
        raise ValueError("Capture hash mismatch: " + name)
    with Image.open(directory / (name + ".png")) as image:
        return image.convert("RGBA")


def compare(saved, fresh):
    before = json.loads((saved / "manifest.json").read_text())
    after = json.loads((fresh / "manifest.json").read_text())
    if after.get("status") != "complete" or not after.get("repeat_pixels_equal"):
        raise ValueError("Fresh capture must be complete and repeatable")
    new_rows = rows(after)
    first = checked_image(fresh, new_rows[0])
    repeat = next(row for row in new_rows if row["name"] == "repeat-end")
    last = checked_image(fresh, repeat)
    if first.size != last.size or first.tobytes() != last.tobytes():
        raise ValueError("Fresh repeated control pixels differ")
    # The original barcode archive stores model and firmware in one field.
    if before.get("schema") == "zpl-printer-barcode-comparison-v1":
        expected = f"{after['device']}; firmware {after['firmware']}"
        if before["device"] != expected:
            raise ValueError("Printer identity mismatch: device/firmware")
        before["device"] = after["device"]
    for key in ("device", "firmware", "dpi", "host"):
        if key in before and before[key] != after.get(key):
            raise ValueError("Printer identity mismatch: " + key)
    previous = {row["name"]: row for row in rows(before)}
    if len(previous) != len(rows(before)) or len({r["name"] for r in new_rows}) != len(
        new_rows
    ):
        raise ValueError("Duplicate capture name")
    results = []
    for row in new_rows:
        name = row["name"]
        if name not in previous:
            if name == "repeat-end":
                continue
            raise ValueError("Unexpected fresh case: " + name)
        old = previous[name]
        if old["zpl_sha256"] != row["zpl_sha256"]:
            raise ValueError("Source changed: " + name)
        a = checked_image(saved, old)
        b = checked_image(fresh, row)
        equal = a.size == b.size and a.tobytes() == b.tobytes()
        result = {
            "name": name,
            "zpl_sha256": row["zpl_sha256"],
            "previous_png_sha256": old.get("png_sha256", old.get("printer_png_sha256")),
            "recaptured_png_sha256": row["png_sha256"],
            "previous_dimensions": list(a.size),
            "recaptured_dimensions": list(b.size),
            "pixels_equal": equal,
            "captured_utc": row["captured_utc"],
            "submitted_sha256": row["submitted_sha256"],
        }
        if a.size == b.size:
            # Include alpha differences; RGBA.getbbox() alone only tests alpha.
            difference = ImageChops.difference(a, b)
            channels = difference.split()
            nonzero = channels[0]
            for channel in channels[1:]:
                nonzero = ImageChops.lighter(nonzero, channel)
            result["changed_pixels"] = a.width * a.height - nonzero.histogram()[0]
        results.append(result)
    names = {r["name"] for r in results}
    missing = sorted(set(previous) - names)
    return {
        "schema": 1,
        "saved_reference": saved.as_posix(),
        "saved_manifest_sha256": sha((saved / "manifest.json").read_bytes()),
        "fresh_manifest_sha256": sha((fresh / "manifest.json").read_bytes()),
        "device": after["device"],
        "firmware": after["firmware"],
        "method": after["method"],
        "captured_utc": after["captured_utc"],
        "preview_reset_zpl": after["preview_reset_zpl"],
        "repeat_pixels_equal": True,
        "equal": sum(r["pixels_equal"] for r in results),
        "changed": sum(not r["pixels_equal"] for r in results),
        "not_recaptured": missing,
        "failures": after.get("failures", []),
        "cases": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("saved", type=Path)
    parser.add_argument("fresh", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.saved, args.fresh)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"{report['equal']} identical; {report['changed']} changed; "
        f"{len(report['not_recaptured'])} not recaptured"
    )
    raise SystemExit(bool(report["changed"] or report["not_recaptured"]))


if __name__ == "__main__":
    main()
