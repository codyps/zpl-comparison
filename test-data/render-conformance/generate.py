#!/usr/bin/env python3
"""Deterministic, renderer-independent ZPL conformance fixtures.

Authority: docs/zpl-zbi2-pg-en.pdf, P1134473-11EN Rev A. Each manifest
entry links command sections by the page numbers in zpl-command-index.tsv.
No rasterizer output is an oracle. See README.md for scope and exclusions.
"""

import argparse
import base64
import binascii
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import zlib

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PREFIX = b"^XA^PW832^LL1218^LH0,0^LS0^LT0^PON^LRN^FWN^CI27^CF0,32,0^BY2,3,60"
# Explicitly enumerate label-content commands; never allow arbitrary B*/F*/G*.
ALLOWED = set(
    "A B0 B1 B2 B3 B4 B5 B7 B8 B9 BA BB BC BD BE BF BI BJ BK BL BM BO BP BQ BR BS BT BU BX BY BZ CF CI CV FB FD FE FH FM FN FO FP FR FS FT FV FW FX GB GC GD GE GF GS LH LL LR LS LT PA PM PO PW SF SN TB XA XZ".split()
)
PAGES = dict(
    line.split("\t")
    for line in (REPO / "docs/zpl-command-index.tsv").read_text().splitlines()
    if line.startswith(("^", "~"))
)


def commands(data):
    """Inventory default-prefix streams; honor GFB byte counts, not payload tokens."""
    result = set()
    pos = 0
    while pos < len(data):
        if data[pos] not in (94, 126):
            pos += 1
            continue
        if data[pos] == 126:
            raise ValueError("Control command outside binary payload")
        code = data[pos + 1 : pos + 3].decode("ascii")
        if code.startswith("A") and code != "A@":
            code = "A"
        if code not in ALLOWED:
            raise ValueError(f"Non-content command: {code}")
        result.add("^" + code)
        if code == "GF":
            binary = re.match(rb"\^GFB,(\d+),(\d+),(\d+),", data[pos:])
            if binary:
                pos += binary.end() + int(binary[1])
                continue
        pos += 3
    return sorted(result)


def rows():
    result = []

    def add(
        name,
        group,
        purpose,
        body,
        *,
        validity="valid",
        oracle="printer",
        relation=None,
        source=None,
        document=False,
    ):
        if isinstance(body, str):
            body = body.encode("utf-8")
        data = body if document else PREFIX + body + b"^XZ\n"
        codes = commands(data)
        result.append(
            dict(
                name=name,
                group=group,
                purpose=purpose,
                validity=validity,
                oracle=oracle,
                relation=relation,
                source=source,
                commands=codes,
                width=832,
                height=1218,
                zpl=data,
            )
        )

    # Preserve earlier independent probes byte-for-byte; no old pixels promoted to new truth.
    spec = importlib.util.spec_from_file_location(
        "argument_probes", REPO / "benchmarks/accuracy/cases.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for probe in module.probes(explicit_defaults=False):
        if probe["group"] == "repeatability":
            continue
        add(
            "probe-" + probe["name"],
            "baseline-" + probe["group"],
            probe["command"] + " " + probe["arguments"],
            probe["zpl"],
            document=True,
            source="benchmarks/accuracy/cases.py",
        )
        result[-1]["width"], result[-1]["height"] = probe["width"], probe["height"]
    for path in sorted(
        (REPO / "references/barcodes-zd621-v1").glob("*.zpl")
    ):
        add(
            "symbol-" + path.stem,
            "barcode-families",
            "Reference symbol variant: " + path.stem,
            # Preserve the separately versioned conformance corpus inputs.
            # The accuracy suite now recaptures these symbols at PW832.
            path.read_bytes().replace(b"^PW832", b"^PW812"),
            document=True,
            source=str(path.relative_to(REPO)),
        )
        result[-1]["width"] = 812

    # Font metrics: resident bitmap/scalable families, scale quantization and anchoring.
    for font in "0ABCDEFGH":
        for rotation in "NRIB":
            add(
                f"font-{font}-{rotation}",
                "fonts",
                f"Resident font {font}, rotation {rotation}, punctuation, ascenders and descenders",
                f"^FO360,500^A{font}{rotation},32,24^FDHgypqj 0123!?^FS",
                oracle="font-dependent",
            )
    for font in "123456789IJKLMNOPQRSTUVWXYZ":
        add(
            f"font-id-{font}",
            "fonts",
            f"Resident/logical font selector {font}; availability and fallback are device-dependent, no font file loaded",
            f"^FO80,100^A{font}N,32,24^FDHgypqj 0123^FS",
            oracle="font-dependent",
        )
    for height, width in [
        (0, 0),
        (1, 1),
        (2, 2),
        (7, 0),
        (15, 0),
        (17, 0),
        (31, 0),
        (33, 0),
        (63, 0),
        (65, 0),
        (32, 1),
        (1, 32),
        (64, 16),
        (16, 64),
        (96, 96),
    ]:
        add(
            f"font-dim-{height}-{width}",
            "fonts",
            f"Default dimensions, small-size rounding or anisotropic scale: {height},{width}",
            f"^FO100,160^A0N,{height},{width}^FDWim Hg09^FS",
        )
    for char_class, text in [
        ("digits", "0123456789"),
        ("case", "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz"),
        ("punctuation", "!\"#$%&'()*+,-./:;<=>?@[\\]_`{|}"),
        ("spacing", "  a  b   c  "),
        ("empty", ""),
    ]:
        add(
            "text-" + char_class,
            "text-data",
            "Field data " + char_class + "; whitespace must not be trimmed",
            "^FO30,120^A0N,24,12^FD" + text + "^FS",
        )
    for size in [1, 48, 400]:
        body = "".join(
            f"^FO{20 + (i % 12) * 65},{20 + (i // 12) * 32}^A0N,20,10^FD{i:03d}^FS"
            for i in range(size)
        )
        add(
            f"fields-{size}",
            "stress",
            f"{size} independent text fields; detect leakage, dropping and scalability",
            body,
        )
    add(
        "field-data-3072-bytes",
        "stress",
        "3072-byte field; clipped to canvas, no implicit truncation before layout",
        "^FO0,0^A0N,16,8^FB800,60,0,L,0^FD" + "ABCD " * 614 + "AB" + "^FS",
        validity="boundary",
    )
    add(
        "field-defaults",
        "state",
        "CF applies to following fields; omitted A dimensions, explicit overrides and subsequent default use",
        "^CF0,24,16^FO40,40^FDDefault^FS^FO40,100^A0N,48,32^FDOverride^FS^FO40,180^FDDefault again^FS",
    )
    for rot in "NRIB":
        for origin in ["FO", "FT"]:
            for just in [0, 1, 2]:
                add(
                    f"anchor-{origin}-{rot}-{just}",
                    "position",
                    f"{origin} origin, {rot} rotation, justification {just}; crosshair stays fixed",
                    f"^FO396,390^GB9,1,1^FS^FO400,386^GB1,9,1^FS^{origin}400,390,{just}^A0{rot},40,22^FDHgyp^FS",
                )
    for axis, value in [
        ("LS", -80),
        ("LS", 80),
        ("LT", -50),
        ("LT", 50),
        ("LH", "100,200"),
    ]:
        add(
            f"offset-{axis}-{str(value).replace(',', '-')}",
            "position",
            f"{axis}={value}, including clipping at canvas origin",
            f"^{axis}{value}^FO0,0^GB160,80,4^FS^FO30,30^FDOrigin^FS",
            validity="boundary",
        )
    for pos in [(0, 0), (831, 1217), (832, 1218), (800, 1180), (32000, 32000)]:
        add(
            f"clip-{pos[0]}-{pos[1]}",
            "clipping",
            f"Field at {pos}; exact edge/partly/fully outside page; no wraparound",
            f"^FO{pos[0]},{pos[1]}^GB60,60,4^FS",
            validity="boundary",
        )
    for pm, po in [("N", "N"), ("Y", "N"), ("N", "I"), ("Y", "I")]:
        add(
            f"page-transform-{pm}-{po}",
            "transforms",
            f"Mirror={pm}, invert={po}; asymmetric page landmarks and text",
            f"^PM{pm}^PO{po}^FO20,40^GB70,130,7^FS^FO140,100^FDTop left 123^FS^FO720,1080^GC60,9^FS",
        )
    add(
        "label-reverse",
        "compositing",
        "LR reverse with overlapping shapes and text; compare to plain label",
        "^LRY^FO40,40^GB160,120,6^FS^FO70,90^FDReverse^FS",
    )
    for direction in "HVR":
        for gap in [0, 1, 8]:
            add(
                f"field-direction-{direction}-{gap}",
                "text-layout",
                f"FP {direction}, extra gap {gap}; semantics independent of rotation",
                f"^FO300,400^FP{direction},{gap}^A0N,32,24^FDAB12^FS",
            )
    for width in [1, 20, 120, 300]:
        for align in "LCRJ":
            add(
                f"block-{width}-{align}",
                "text-layout",
                f"FB width {width}, alignment {align}, wrapping long words and spaces, three-line overflow",
                f"^FO100,100^A0N,28,14^FB{width},3,0,{align},0^FDOne two SUPERCALIFRAGILISTIC four five six seven eight^FS",
                validity="boundary" if width < 28 else "valid",
            )
    for spacing, indent in [(-12, 0), (12, 0), (0, 40), (8, 80)]:
        add(
            f"block-spacing-{spacing}-indent-{indent}",
            "text-layout",
            f"FB signed line spacing {spacing} and hanging indent {indent}",
            f"^FO80,80^A0N,28,14^FB240,5,{spacing},L,{indent}^FDOne two three four five six seven eight nine ten^FS",
        )
    for name, text in [
        ("breaks", "One\\&\\&Three\\&"),
        ("long-word", "UNBREAKABLEWORD" * 5),
        ("spaces", "  Leading  and   repeated   spaces  "),
        ("empty", ""),
    ]:
        add(
            "block-content-" + name,
            "text-layout",
            "FB content edge: " + name,
            f"^FO80,80^A0N,28,14^FB220,3,0,L,0^FD{text}^FS",
        )
    for orientation in "NRIB":
        for height in [1, 40, 120]:
            add(
                f"text-block-{orientation}-{height}",
                "text-layout",
                f"TB {orientation}, 220x{height}; height truncation, word wrap and angle escape",
                f"^FO350,500^A0N,28,14^TB{orientation},220,{height}^FDOne two three four five << > six seven^FS",
                validity="boundary" if height == 1 else "valid",
            )

    # Unicode cases are explicitly font-dependent: absence is not a promise to install fonts.
    for name, text in [
        ("latin", "Café Ångström £ €"),
        ("combining", "é e\u0301 Å A\u030a"),
        ("greek", "Ελληνικά"),
        ("cyrillic", "Привет"),
        ("hebrew", "שלום 123 ABC"),
        ("arabic", "مرحبا 123 ABC"),
        ("cjk", "日本語 中文 한국어"),
        ("supplementary", "A😀B"),
        ("controls", "A\u200bB\u00a0C\u00adD"),
        ("missing", "A\u0378B"),
    ]:
        payload = text.encode("utf-8")
        escaped = "".join(f"_{byte:02X}" for byte in payload)
        add(
            "unicode-" + name,
            "encoding",
            "UTF-8 "
            + name
            + "; resident glyph availability and shaping must be recorded",
            "^CI28^FO80,100^A0N,40,24^FH_^FD" + escaped + "^FS",
            oracle="font-dependent",
        )
    for mode in [0, 13, 27, 28, 29, 30, 31, 33, 34, 35, 36]:
        # UTF-16 data must really be UTF-16; use FH to keep the standalone file inspectable.
        data = "ABC 123".encode(
            "utf-16-be" if mode == 29 else "utf-16-le" if mode == 30 else "ascii"
        )
        add(
            f"encoding-{mode}",
            "encoding",
            f"CI {mode}: ASCII repertoire in the requested byte encoding",
            f"^CI{mode}^FO80,100^FH_^FD" + "".join(f"_{b:02X}" for b in data) + "^FS",
            oracle="font-dependent",
        )
    add(
        "encoding-remap",
        "encoding",
        "CI source/destination glyph remapping pair 65,66",
        "^CI0,65,66^FO80,100^FDABBA^FS",
    )
    for flags in ["0,0,0,0", "1,0,0,0", "0,1,0,0", "0,0,1,0", "0,0,0,1", "1,1,1,1"]:
        add(
            "advanced-text-" + flags.replace(",", ""),
            "encoding",
            "PA default glyph/bidi/shaping/OpenType flags "
            + flags
            + "; no downloaded fonts",
            "^CI28^PA" + flags + "^FO80,100^A0N,40,24^FDABC שלום مرحبا \u0378^FS",
            oracle="font-dependent",
        )
    for indicator in ["_", "#"]:
        payload = "".join(indicator + f"{b:02X}" for b in b"^~_,\\&ABC\x00\x7f")
        add(
            "hex-" + ("underscore" if indicator == "_" else "hash"),
            "lexical",
            "FH escapes command prefixes, delimiters, backslash, NUL and DEL inside field data",
            f"^FO80,100^FH{indicator}^FD{payload}^FS",
            validity="boundary",
        )
    add(
        "hex-scope",
        "state",
        "FH applies to one field; the following literal _41 must remain literal",
        "^FO80,80^FH_^FD_41^FS^FO80,140^FD_41^FS",
    )
    add(
        "variable-field",
        "text-data",
        "FV literal text followed by FD literal text",
        "^FO80,80^FVVariable^FS^FO80,140^FDFixed^FS",
    )
    add(
        "numbered-fields-inline",
        "state",
        "FN reuse entirely inside one label; no stored-format operations",
        "^FO80,80^FN1^FDShared text^FS^FO80,140^FN1^FS",
    )
    for name, expression in [
        ("whole", "#1# / #2#"),
        ("forward", "#1,f,2,3#"),
        ("backward", "#1,b,1,3#"),
        ("past-end", "#1,f,2,99#"),
    ]:
        add(
            "field-concat-" + name,
            "text-data",
            "FE inline numbered-field concatenation / substring: " + name,
            "^FO80,40^FN1^FDABCDEFG^FS^FO80,90^FN2^FD12345^FS^FO80,160^FE#^FD"
            + expression
            + "^FS",
        )
    add(
        "field-concat-scope",
        "state",
        "FE affects only its following FD, subsequent #1# stays literal",
        "^FO80,40^FN1^FDABC^FS^FO80,100^FE#^FD#1#^FS^FO80,160^FD#1#^FS",
    )
    add(
        "interleaved-odd-digits",
        "barcode-arguments",
        "Odd-length Interleaved 2 of 5 input; documented automatic leading zero",
        "^FO80,80^B2N,60,N,N,N^FD12345^FS",
        validity="boundary",
    )
    for start, increment, zero in [
        ("000009", "1", "Y"),
        ("000009", "1", "N"),
        ("A009Z", "-1", "Y"),
    ]:
        add(
            f"serial-{start}-{zero}",
            "serialization",
            "SN initial visible value only; increment across physical prints is intentionally untested",
            f"^FO80,80^SN{start},{increment},{zero}^FS",
        )
    add(
        "serial-mask",
        "serialization",
        "SF alphabetic/numeric mask, initial label only",
        "^FO80,80^FDBL0000^SFAAdddd,1^FS",
    )
    add(
        "comments-and-line-endings",
        "lexical",
        "FX comments and CR/LF between fields should not create ink",
        b"^FXNo ink from this comment^FS\r\n^FO80,80^FDVisible^FS\n",
    )

    for rounding in range(9):
        add(
            f"box-rounding-{rounding}",
            "shapes",
            f"GB corner rounding {rounding} of 0..8",
            f"^FO80,80^GB160,100,5,B,{rounding}^FS",
        )
    for w, h, t in [
        (0, 80, 1),
        (80, 0, 1),
        (1, 1, 1),
        (2, 2, 1),
        (31, 31, 1),
        (32, 32, 1),
        (33, 33, 1),
        (100, 60, 30),
        (100, 60, 100),
    ]:
        add(
            f"box-{w}-{h}-{t}",
            "shapes",
            f"GB degenerate, pixel-size, odd/even or fill boundary: {w},{h},{t}",
            f"^FO80,80^GB{w},{h},{t},B^FS",
            validity="boundary",
        )
    for cmd, shape in [("GC", "61,3"), ("GE", "101,61,3"), ("GD", "101,61,3")]:
        for color in "BW":
            for direction in ["L", "R"] if cmd == "GD" else [""]:
                add(
                    f"shape-{cmd}-{color}-{direction or 'plain'}",
                    "shapes",
                    f"{cmd} {color} on black backing, odd dimensions " + direction,
                    "^FO60,60^GB150,110,110,B^FS"
                    + f"^FO80,80^{cmd}{shape},{color}"
                    + ("," + direction if direction else "")
                    + "^FS",
                )
    for symbol in "ABCDE":
        for orientation in "NRIB":
            add(
                f"symbol-graphic-{symbol}-{orientation}",
                "shapes",
                f"GS symbol selector {symbol}, orientation {orientation}",
                f"^FO350,500^GS{orientation},48,48^FD{symbol}^FS",
            )
    for sequence in ["black-white", "white-black", "reverse-overlap", "reverse-twice"]:
        black = "^FO80,80^GB140,100,100,B^FS"
        white = "^FO100,100^GB100,60,60,W^FS"
        reverse = "^FO100,100^FR^GB100,60,60,B^FS"
        body = {
            "black-white": black + white,
            "white-black": white + black,
            "reverse-overlap": black + reverse,
            "reverse-twice": black + reverse + reverse,
        }[sequence]
        add(
            "paint-" + sequence,
            "compositing",
            "Draw order and XOR/reverse semantics: " + sequence,
            body,
        )
    add(
        "reverse-field-scope",
        "state",
        "FR on one field must not leak to following normal text",
        "^FO60,60^GB280,140,140^FS^FO80,80^FR^FDA^FS^FO80,240^FDB^FS",
    )

    # Inline raster representations encode exactly the same 16x8 asymmetric bit pattern.
    raw = bytes.fromhex("FF00810081808140812081108108FFFF")
    representations = {"hex": raw.hex().upper().encode()}
    # A second, deliberately simple RLE pair uses comma fill and colon repeat.
    for encoding in ["B64", "Z64"]:
        payload = base64.b64encode(zlib.compress(raw, 9) if encoding == "Z64" else raw)
        representations[encoding] = (
            b":"
            + encoding.encode()
            + b":"
            + payload
            + b":"
            + f"{binascii.crc_hqx(payload, 0):04X}".encode()
        )
    for encoding, payload in representations.items():
        add(
            "raster-equivalent-" + encoding,
            "graphics",
            "Same 16x8 inline image in " + encoding,
            b"^FO80,80^GFA,16,16,2," + payload + b"^FS",
            relation={"kind": "same-raster", "set": "inline-16x8"},
        )
    add(
        "raster-equivalent-binary",
        "graphics",
        "Same 16x8 image as counted binary data",
        b"^FO80,80^GFB,16,16,2," + raw + b"^FS",
        relation={"kind": "same-raster", "set": "inline-16x8"},
    )
    for name, payload in [("hex", b"0000FFFF0000FFFF"), ("rle", b",!,!")]:
        add(
            "raster-fill-" + name,
            "graphics",
            "16x4 alternating empty/full rows; comma/! terminate rows",
            b"^FO80,80^GFA,8,8,2," + payload + b"^FS",
            relation={"kind": "same-raster", "set": "rle-fill"},
        )
    for name, payload in [("hex", b"AA55AA55AA55AA55"), ("rle", b"HAH5:::")]:
        # H means repeat two hex nibbles; HA H5 encodes AA55, then ':' repeats rows.
        add(
            "raster-repeat-" + name,
            "graphics",
            "16x4 AA55 row; repeat count and colon repeat",
            b"^FO80,80^GFA,8,8,2," + payload + b"^FS",
            relation={"kind": "same-raster", "set": "rle-repeat"},
        )
    add(
        "raster-binary-command-bytes",
        "graphics",
        "Binary bytes resemble ^FS/~HS; counted payload must not be parsed as commands",
        b"^FO80,80^GFB,8,8,1,^FS~HS\x00\xff^FS",
        validity="boundary",
    )
    for bpr in [1, 2, 3, 17]:
        payload = bytes([0x81] * bpr * 7)
        add(
            f"raster-stride-{bpr}",
            "graphics",
            f"Packed MSB-first raster, {bpr} bytes/row, 7 rows",
            f"^FO81,83^GFA,{len(payload)},{len(payload)},{bpr},"
            + payload.hex().upper()
            + "^FS",
        )
    add(
        "raster-clipped",
        "graphics",
        "Inline raster clipped at bottom-right edge",
        b"^FO828,1214^GFA,16,16,2," + raw.hex().upper().encode() + b"^FS",
        validity="boundary",
    )

    for module in [1, 2, 3, 10]:
        for ratio in ["2.0", "2.5", "3.0"]:
            add(
                f"barcode-module-{module}-ratio-{ratio}",
                "barcode-arguments",
                f"BY module width {module}, ratio {ratio}; Code39",
                f"^FO40,80^BY{module},{ratio},80^B3N,N,80,N,N^FDABC^FS",
                validity="boundary" if module == 10 else "valid",
            )
    for mode in "NUAD":
        add(
            "code128-mode-" + mode,
            "barcode-arguments",
            "Code128 mode " + mode + "; numeric payload",
            f"^FO80,100^BCN,80,N,N,N,{mode}^FD"
            + (
                {"U": "1234567890123456789", "D": "(01)12345678901231(10)ABC"}.get(
                    mode, "123456789012"
                )
            )
            + "^FS",
        )
    for name, payload in [
        ("subset-b", ">:Abc123"),
        ("subset-c", ">;12345678"),
        ("switch", ">:AB>51234>6CD"),
        ("fnc1", ">;>80112345678901231"),
    ]:
        add(
            "code128-" + name,
            "barcode-arguments",
            "Code128 explicit invocation: " + name,
            "^FO80,100^BCN,80,N,N,N,N^FD" + payload + "^FS",
        )
    for command, data in [
        ("B2", "12345678"),
        ("B3", "ABC123"),
        ("BC", "ABC123"),
        ("BE", "123456789012"),
        ("BU", "01234567890"),
    ]:
        for rot in "NRIB":
            params = rot + ",N,70,Y,Y" if command == "B3" else rot + ",70,Y,Y"
            add(
                f"readable-{command}-{rot}",
                "barcode-arguments",
                "Readable text above rotated "
                + command
                + "; measure caption position as well as bars",
                f"^FO350,500^{command}{params}^FD{data}^FS",
            )
    for mask in range(8):
        add(
            f"qr-mask-full-{mask}",
            "barcode-arguments",
            f"QR mask {mask}, model2/ECM",
            f"^FO80,100^BQN,2,4,M,{mask}^FDMA,0123456789ABC^FS",
        )
    for quality in [0, 50, 80, 100, 140, 200]:
        add(
            f"datamatrix-quality-{quality}",
            "barcode-arguments",
            f"Data Matrix quality {quality}; legacy ECC modes versus ECC200",
            f"^FO80,100^BXN,4,{quality}^FDABC123^FS",
        )
    for columns, rows_count in [(10, 10), (16, 16), (18, 8), (32, 8)]:
        add(
            f"datamatrix-size-{columns}-{rows_count}",
            "barcode-arguments",
            f"ECC200 explicit columns={columns},rows={rows_count}",
            f"^FO80,100^BXN,3,200,{columns},{rows_count},6,_,{1 if columns == rows_count else 2}^FDAB12^FS",
        )
    for security in [0, 2, 8]:
        for truncated in "NY":
            add(
                f"pdf417-security-{security}-{truncated}",
                "barcode-arguments",
                f"PDF417 EC={security}, truncated={truncated}, automatic rows",
                f"^FO40,80^BY2^B7N,3,{security},6,,{truncated}^FDThe quick brown fox 0123456789^FS",
            )
    for count in [1, 3]:
        origins = ",".join(f"{40 + i * 240},80" for i in range(count))
        add(
            f"pdf417-structured-origins-{count}",
            "barcode-arguments",
            "FM structured append origins; insufficient origins may intentionally suppress symbols",
            f"^FM{origins}^BY1^B7N,2,0,3,10,N^FD"
            + ("Structured append 0123456789 " * 25)
            + "^FS",
            validity="boundary",
        )
    for code in ["B7", "BF"]:
        config = "N,2,0,3,10,N" if code == "B7" else "N,2,1"
        add(
            f"structured-exclude-{code}",
            "barcode-arguments",
            "FM excluded second origin (e,e), bounded structured append payload",
            f"^FM40,80,e,e,500,80^BY1^{code}{config}^FD"
            + ("Append 0123456789 " * 30)
            + "^FS",
            validity="boundary",
        )
    add(
        "barcode-validation",
        "barcode-arguments",
        "CV validation enabled with valid Code128 data",
        "^CVY^FO80,100^BCN,60,N,N,N,N^FDABC123^FS",
    )
    add(
        "barcode-default-scope",
        "state",
        "BY height/width defaults followed by per-symbol override",
        "^BY1,2,40^FO40,80^BCN,,N,N^FD1234^FS^BY3,3,80^FO40,200^BCN,30,N,N^FD1234^FS",
    )

    # Metamorphic pairs: useful without any trusted font or barcode implementation.
    plain = "^FO80,100^A0N,32,20^FDABC123^FS"
    add(
        "equivalent-text-plain",
        "metamorphic",
        "Plain ASCII text",
        plain,
        relation={"kind": "same-raster", "set": "text-escape"},
    )
    add(
        "equivalent-text-hex",
        "metamorphic",
        "Hex-escaped equivalent ASCII text",
        "^FO80,100^A0N,32,20^FH_^FD_41_42_43_31_32_33^FS",
        relation={"kind": "same-raster", "set": "text-escape"},
    )
    add(
        "equivalent-home-direct",
        "metamorphic",
        "Direct field origin",
        "^FO110,140^GB100,60,4^FS",
        relation={"kind": "same-raster", "set": "origin-home"},
    )
    add(
        "equivalent-home-offset",
        "metamorphic",
        "LH + FO is equivalent direct translation",
        "^LH30,40^FO80,100^GB100,60,4^FS",
        relation={"kind": "same-raster", "set": "origin-home"},
    )
    add(
        "equivalent-comment",
        "metamorphic",
        "Comment does not affect pixels",
        "^FXA comment^FS" + plain,
        relation={"kind": "same-raster", "set": "text-escape"},
    )

    # Dense visual pages: deliberately asymmetric; no "PASS" text that could fake a pass.
    typography = ""
    for i, font in enumerate("0ABCDEFGH"):
        y = 30 + i * 125
        typography += f"^FO20,{y}^GB790,110,1^FS^FO30,{y + 10}^A0N,20,12^FDFont {font}^FS^FO160,{y + 20}^A{font}N,32,24^FDHamburgefonts 0123!?^FS^FO650,{y + 90}^A{font}I,24,16^FDgyp^FS"
    add(
        "torture-typography",
        "torture",
        "Resident font atlas: mixed sizes, rotations, baselines and panel boundaries",
        typography,
        oracle="font-dependent",
    )
    grid = ""
    for i in range(36):
        x = 20 + (i % 6) * 132
        y = 20 + (i // 6) * 185
        rot = "NRIB"[i % 4]
        rounding = i % 9
        grid += f"^FO{x},{y}^GB120,170,{1 + i % 5},B,{rounding}^FS^FO{x + 20},{y + 25}^GC{20 + i},2^FS^FO{x + 10},{y + 95}^GD90,50,2,B,{'LR'[i % 2]}^FS^FO{x + 65},{y + 80}^A0{rot},20,10^FD{i:02d}^FS"
    add(
        "torture-geometry",
        "torture",
        "36 panels combine odd/even shapes, rounding, line direction, thickness and rotated labels",
        grid,
    )
    ticket = "^FO20,20^GB792,1178,3^FS^FO40,45^A0N,52,30^FDRENDER CONFORMANCE^FS^FO40,120^GB750,4,4^FS^FO40,150^A0N,28,15^FB440,4,3,J,20^FDMixed text wraps across a justified block with a hanging indent. Small gaps matter.^FS^FO560,160^BQN,2,5,Q,3^FDQA,ZPL-CONFORMANCE-2026^FS^FO40,330^BY2,3,90^BCN,90,Y,N,N,N^FDABC123456789^FS^FO40,490^GB730,120,120^FS^FO60,520^FR^A0N,42,24^FDREVERSED OVER BLACK^FS^FO40,650^BXN,5,200^FDZPL-1234^FS^FO250,650^GB200,110,5,B,8^FS^FO510,650^GE220,110,4^FS^FO40,850^BY2^B7N,4,2,5^FDMixed raster and barcode label^FS^FO420,980^A0I,36,22^FDUPSIDE DOWN^FS^FO740,900^A0B,28,16^FDVERTICAL^FS"
    add(
        "torture-shipping-label",
        "torture",
        "Dense mixed label: text wrapping, QR, Code128, DataMatrix, PDF417, reversal and rotation",
        ticket,
    )
    compositing = "".join(
        f"^FO{30 + (i % 8) * 95},{30 + (i // 8) * 90}^GB140,130,{10 + i % 40},{'BW'[i % 3 == 0]},"
        + str(i % 9)
        + "^FS"
        for i in range(96)
    )
    add(
        "torture-overlap",
        "torture",
        "96 overlapping black/white rounded boxes; order-sensitive raster composition",
        compositing,
    )

    # Negative inputs remain local-only, never printer-capture eligible.
    negatives = [
        ("bad-orientation", "^FO80,80^A0Q,32,20^FDABC^FS"),
        ("negative-width", "^FO80,80^GB-1,60,3^FS"),
        ("bad-alignment", "^FO80,80^FB200,3,0,Z,0^FDABC^FS"),
        ("bad-hex", "^FO80,80^FH_^FD_4G^FS"),
        ("truncated-hex", "^FO80,80^FH_^FDABC_4^FS"),
        ("bad-raster-count", "^FO80,80^GFA,8,8,1,FF^FS"),
        ("zero-raster-stride", "^FO80,80^GFA,1,1,0,FF^FS"),
        ("bad-base64", "^FO80,80^GFA,8,8,1,:B64:!!!!:0000^FS"),
        ("bad-crc", "^FO80,80^GFA,8,8,1,:B64:/4GBgYGBgf8=:0000^FS"),
        ("qr-model-invalid", "^FO80,80^BQN,3,4,L,0^FDLA,ABC^FS"),
        ("qr-mask-invalid", "^FO80,80^BQN,2,4,L,8^FDLA,ABC^FS"),
        ("ean-nonnumeric", "^FO80,80^BEN,60,N,N^FDABCDEFGHIJKL^FS"),
        ("code39-empty", "^FO80,80^B3N,N,60,N,N^FD^FS"),
        ("unknown-encoding", "^CI999^FO80,80^FDABC^FS"),
    ]
    for name, body in negatives:
        add(
            "invalid-" + name,
            "negative",
            "Malformed/out-of-range input: "
            + name
            + "; observe rejection/fallback, never count as valid fidelity",
            body,
            validity="invalid",
            oracle="behavior-only",
        )
    return result


def artifacts():
    cases = rows()
    assert len({c["name"] for c in cases}) == len(cases)
    files = {}
    entries = []
    for c in cases:
        data = c.pop("zpl")
        filename = f"cases/{c['group']}/{c['name']}.zpl"
        files[filename] = data
        entries.append(
            {
                **c,
                "file": filename,
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "capture_eligible": c["validity"] != "invalid",
                "references": [
                    {"command": cmd, "pdf_page": int(PAGES[cmd])}
                    for cmd in c["commands"]
                ],
            }
        )
    manifest = {
        "schema": 1,
        "suite": "render-conformance-v1",
        "reference": "Zebra Programming Guide P1134473-11EN Rev A",
        "cases": entries,
    }
    files["manifest.json"] = (
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    ).encode()
    inventory = {
        cmd: [c["name"] for c in entries if cmd in c["commands"]]
        for cmd in sorted(PAGES)
    }
    out = [
        "# Rendering corpus coverage\n",
        "Generated by `generate.py`; this is test presence, not a claim that a renderer passes or all values are covered.\n",
        "[Usage and scope](README.md) · [Machine-readable manifest](manifest.json) · [Zebra reference](../../docs/zpl-zbi2-pg-en.pdf)\n",
        "## Command scope\n",
        "| Command | Guide page | Cases | Disposition |",
        "| --- | --- | --- | --- |",
    ]
    for cmd, names in inventory.items():
        if names:
            first = next(c for c in entries if c["name"] == names[0])
            status = f"[Exercised]({first['file']})"
        elif cmd in ["^A@", "^CW", "^FL", "^FN", "^XG", "^XF", "^IM", "^IL"]:
            status = "Excluded: stored font/graphic/format dependency"
        elif cmd in ["^FC"]:
            status = "Excluded: clock-dependent data; requires controlled printer clock"
        elif cmd in ["^CC", "~CC", "^CD", "~CD", "^CT", "~CT", "^MU", "^SZ"]:
            status = "Excluded: parser/unit/language configuration"
        else:
            status = (
                "Excluded: device, transport, storage, job control, diagnostics or RFID"
            )
        out.append(f"| `{cmd}` | {PAGES[cmd]} | {len(names)} | {status} |")
    out += [
        "\n## Case catalog\n",
        "Invalid cases are local-only. Font-dependent cases may legitimately expose missing resident glyphs; they are not font installation tests.\n",
        "| File | Class | Purpose |",
        "| --- | --- | --- |",
    ]
    for c in entries:
        out.append(
            f"| [{c['name']}]({c['file']}) | {c['validity']} / {c['oracle']} | {c['purpose'].replace('|', '/')} |"
        )
    files["COVERAGE.md"] = ("\n".join(out) + "\n").encode()
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    generated = artifacts()
    actual = {str(p.relative_to(HERE)) for p in (HERE / "cases").rglob("*.zpl")}
    stale = actual - set(generated)
    if stale:
        raise SystemExit(f"Stale generated cases: {sorted(stale)}")
    for name, data in generated.items():
        path = HERE / name
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                raise SystemExit(f"Out of date: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print(
        f"{'Verified' if args.check else 'Generated'} {len(generated) - 2} ZPL fixtures"
    )


if __name__ == "__main__":
    main()
