"""Deterministic invalid-input probes, each paired with a valid control."""

import argparse
import base64
import binascii
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def artifacts():
    def label(body):
        if isinstance(body, str):
            body = body.encode()
        return b"^XA^PW400^LL300^FO20,20" + body + b"^FS^XZ"

    def b64(data, encoding="B64"):
        payload = base64.b64encode(data)
        return (
            f":{encoding}:".encode()
            + payload
            + f":{binascii.crc_hqx(payload, 0):04X}".encode()
        )

    bitmap = bytes.fromhex("FF818181818181FF")
    gf = "^GFA,8,8,1,"
    text = "^A0N,32,20^FDABC"
    probes = [
        (
            "missing-end",
            "framing",
            "One complete ^XA...^XZ label is required by this suite.",
            label(text),
            label(text)[:-3],
            "^XA/^XZ",
            "Single-label input contract; streaming framers can intentionally accept fragments.",
        ),
        (
            "truncated-command",
            "framing",
            "A command prefix is missing its two-character command code.",
            label(text),
            label(text)[:-3] + b"^",
            "ZPL command framing",
            "A streaming framer may wait for more bytes.",
        ),
        (
            "raster-invalid-hex",
            "malformed",
            "Question marks are not hexadecimal digits or graphic RLE tokens.",
            label(gf + "FF818181818181FF"),
            label(gf + "??818181818181FF"),
            "^GF, guide p. 215",
            "Malformed graphic data.",
        ),
        (
            "raster-short-data",
            "malformed",
            "Eight graphic bytes are declared but only two are supplied.",
            label(gf + "FF818181818181FF"),
            label(gf + "FF81"),
            "^GF, guide p. 215",
            "A command prefix may abort a download; acceptance can mean recovery, not complete decoding.",
        ),
        (
            "binary-truncated",
            "malformed",
            "Eight binary bytes are declared but the stream ends after one.",
            label(b"^GFB,8,8,1," + bitmap),
            b"^XA^PW400^LL300^FO20,20^GFB,8,8,1,\xff",
            "^GF, guide p. 215",
            "EOF occurs inside counted data; no printer is contacted.",
        ),
        (
            "base64-alphabet",
            "malformed",
            "Exclamation marks are outside the Base64 alphabet.",
            label(gf.encode() + b64(bitmap)),
            label(gf + ":B64:!!!!:0000"),
            "Zebra alternate data encoding",
            "Tests encoded graphic decoding.",
        ),
        (
            "base64-crc",
            "malformed",
            "The supplied checksum differs from CRC-16 of the encoded payload.",
            label(gf.encode() + b64(bitmap)),
            label(gf.encode() + b64(bitmap)[:-4] + b"1234"),
            "Zebra alternate data encoding",
            "Control uses the correct checksum.",
        ),
        (
            "z64-invalid-stream",
            "malformed",
            "Valid Base64 and CRC wrap bytes that are not a zlib stream.",
            label(gf.encode() + b64(__import__("zlib").compress(bitmap), "Z64")),
            label(gf.encode() + b64(bitmap, "Z64")),
            "Zebra alternate data encoding",
            "Control uses zlib-compressed graphic bytes.",
        ),
        (
            "ean-nonnumeric",
            "malformed",
            "EAN-13 data contains letters instead of numeric digits.",
            label("^BEN,60,N,N^FD123456789012"),
            label("^BEN,60,N,N^FDABCDEFGHIJKL"),
            "^BE, guide p. 109",
            "Only tests input rejection, not scanner validity.",
        ),
        (
            "orientation",
            "fallback",
            "Q is outside the N/R/I/B orientation values.",
            label(text),
            label("^A0Q,32,20^FDABC"),
            "^A",
            "Defaulting/ignoring may be intentional; no strict rejection pass/fail.",
        ),
        (
            "negative-width",
            "fallback",
            "A box width is negative.",
            label("^GB20,20,3"),
            label("^GB-1,20,3"),
            "^GB",
            "Clamping/defaulting may be intentional.",
        ),
        (
            "alignment",
            "fallback",
            "Z is outside the field-block alignment values.",
            label("^A0N,32,20^FB200,3,0,L,0^FDABC"),
            label("^A0N,32,20^FB200,3,0,Z,0^FDABC"),
            "^FB",
            "Defaulting/ignoring may be intentional.",
        ),
        (
            "field-hex",
            "fallback",
            "An enabled field escape contains a nonhex digit.",
            label("^A0N,32,20^FH_^FD_41"),
            label("^A0N,32,20^FH_^FD_4G"),
            "^FH",
            "Some APIs preserve malformed escapes literally.",
        ),
        (
            "field-hex-truncated",
            "fallback",
            "An enabled field escape has only one hex digit.",
            label("^A0N,32,20^FH_^FD_41"),
            label("^A0N,32,20^FH_^FD_4"),
            "^FH",
            "Some APIs preserve malformed escapes literally.",
        ),
        (
            "zero-stride",
            "fallback",
            "Graphic bytes per row is zero rather than at least one.",
            label(gf + "FF818181818181FF"),
            label("^GFA,8,8,0,FF818181818181FF"),
            "^GF, guide p. 215",
            "Observe rejection or recovery separately from malformed encoding.",
        ),
        (
            "qr-model",
            "fallback",
            "QR model 3 is outside the supported model values.",
            label("^BQN,2,3,L,0^FDLA,ABC"),
            label("^BQN,3,3,L,0^FDLA,ABC"),
            "^BQ",
            "Defaulting/ignoring may be intentional.",
        ),
        (
            "qr-mask",
            "fallback",
            "QR mask 8 is outside the 0..7 range.",
            label("^BQN,2,3,L,0^FDLA,ABC"),
            label("^BQN,2,3,L,8^FDLA,ABC"),
            "^BQ",
            "Defaulting/ignoring may be intentional.",
        ),
        (
            "encoding",
            "fallback",
            "Character encoding 999 is outside the documented selections.",
            label("^CI28" + text),
            label("^CI999" + text),
            "^CI",
            "Defaulting/ignoring may be intentional.",
        ),
    ]
    files = {}
    cases = []
    for name, group, reason, control, invalid, reference, caveat in probes:
        assert control != invalid
        row = dict(
            id=name, group=group, reason=reason, reference=reference, caveat=caveat
        )
        for variant, data in [("control", control), ("invalid", invalid)]:
            path = f"cases/{name}-{variant}.zpl"
            files[path] = data
            row[variant] = dict(
                file=path, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)
            )
        cases.append(row)
    files["manifest.json"] = (
        json.dumps(
            dict(schema=1, suite="invalid-zpl-v1", width=400, height=300, cases=cases),
            indent=2,
        )
        + "\n"
    ).encode()
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    for name, data in artifacts().items():
        path = HERE / name
        if args.check:
            if not path.is_file() or path.read_bytes() != data:
                raise SystemExit(f"Out of date: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print("Verified" if args.check else "Generated", "18 invalid/control pairs")


if __name__ == "__main__":
    main()
