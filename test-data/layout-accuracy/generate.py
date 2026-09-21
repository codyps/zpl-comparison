#!/usr/bin/env python3
"""Font-free layout probes using the existing conformance/capture schema."""

import argparse
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "conformance_generator", HERE.parent / "render-conformance/generate.py"
)
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)


def rows():
    result = []
    # No font defaults or text fields. Reset all page transforms explicitly.
    prefix = "^XA^PW832^LL300^LH0,0^LS0^LT0^PON^PMN^LRN^FWN"

    def add(name, purpose, body, relation=None):
        data = (prefix + body + "^XZ\n").encode("ascii")
        result.append(dict(
            name=name, group="font-free-layout", purpose=purpose,
            validity="valid", oracle="printer", relation=relation, source=None,
            commands=shared.commands(data), width=832, height=300, zpl=data,
        ))

    # Unequal, separated rectangles reveal shifts, reflections and inversion.
    def landmarks(x=0, y=0):
        return (
            f"^FO{40+x},{30+y}^GB71,43,3^FS"
            f"^FO{180+x},{90+y}^GB19,61,19^FS"
            f"^FO{690+x},{210+y}^GB83,27,5^FS"
        )

    add("layout-control", "Asymmetric rectangular landmarks at fixed origins", landmarks())
    home = {"kind": "same-raster", "set": "font-free-home"}
    add("layout-home", "Label home translates all graphic fields", "^LH30,20" + landmarks(), home)
    add("layout-home-direct", "Direct origins equivalent to LH30,20", landmarks(30, 20), home)
    for command, values in [("LS", [-80, 80]), ("LT", [-50, 50])]:
        for value in values:
            add(f"layout-{command}-{value}",
                f"{command}={value}: signed page offset and edge clipping",
                f"^{command}{value}" + landmarks())
    add("layout-offset-combined", "Combined home, horizontal shift and label top",
        "^LH30,20^LS15^LT10" + landmarks())
    for mirror, orientation in [("Y", "N"), ("N", "I"), ("Y", "I")]:
        add(f"layout-transform-{mirror}-{orientation}",
            f"Mirror={mirror}, orientation={orientation}: asymmetric graphic landmarks",
            f"^PM{mirror}^PO{orientation}" + landmarks())
    for name, x, y in [("last-pixel", 831, 299), ("partial", 810, 280), ("outside", 832, 300)]:
        add("layout-clip-" + name,
            "Edge clipping with a visible in-bounds control; no wraparound",
            f"^FO40,30^GB19,11,11^FS^FO{x},{y}^GB43,37,37^FS")
    add("layout-label-reverse", "Label reversal on rectangular landmarks", "^LRY" + landmarks())
    add("layout-field-reverse", "Field reversal inside a solid box; following field remains ordinary",
        "^FO40,30^GB180,110,110^FS^FO70,50^FR^GB71,43,43^FS^FO260,90^GB19,61,19^FS")
    # FW is a field orientation default: use a caption-free barcode rather than
    # assuming that graphic boxes inherit text/barcode rotation semantics.
    for rotation in "NRIB":
        add("layout-field-orientation-" + rotation,
            f"FW={rotation}: Code128 with omitted orientation and both caption flags disabled",
            f"^FW{rotation}^FO400,150^BY1,2,40^BC,40,N,N,N,N^FDAB12^FS")
    return result


def artifacts():
    return shared.artifacts(rows(), suite="font-free-layout-v1")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = artifacts()
    actual = {str(p.relative_to(HERE)) for p in (HERE / "cases").rglob("*.zpl")}
    if actual - set(files):
        raise SystemExit(f"Stale fixtures: {sorted(actual - set(files))}")
    for name, data in files.items():
        path = HERE / name
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                raise SystemExit(f"Out of date: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print(f"{'Verified' if args.check else 'Generated'} {len(files) - 2} font-free layout fixtures")


if __name__ == "__main__":
    main()
