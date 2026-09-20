"""Deterministic argument probes. Zebra guide command/page index: docs/zpl-command-index.tsv.
Only label-preview operations are captured: no persistent downloads, hardware controls or printing.
"""

import base64
import binascii
import zlib


def probes(*, explicit_defaults=True):
    rows = []

    def add(name, group, command, arguments, body):
        prefix = "^XA^PW832^LL300^LH0,0^LS0^LT0^PON^LRN^FWN^BY2,3,100^CI27^CF0,32,0"
        if not explicit_defaults:
            prefix = prefix.replace("^BY2,3,100", "")
        rows.append(
            dict(
                name=name,
                group=group,
                command=command,
                arguments=arguments,
                width=832,
                height=300,
                zpl=(prefix + body + "^XZ").encode(),
            )
        )

    text = "^A0N,32,0^FDHello 123^FS"
    for n in [16, 32, 64]:
        add(
            f"font0-height-{n}",
            "text",
            "^A",
            f"font=0,o=N,h={n},w=0",
            f"^FO80,80^A0N,{n},0^FDHello 123^FS",
        )
    for width in [16, 32, 64]:
        add(
            f"font0-width-{width}",
            "text",
            "^A",
            f"font=0,o=N,h=32,w={width}",
            f"^FO80,80^A0N,32,{width}^FDHello 123^FS",
        )
    for rotation in ["N", "R", "I", "B"]:
        add(
            f"font0-rotation-{rotation}",
            "text",
            "^A",
            f"font=0,o={rotation},h=32,w=0",
            f"^FO250,100^A0{rotation},32,0^FDABC^FS",
        )
    for font in ["A", "D"]:
        add(
            f"font-{font}",
            "text",
            "^A",
            f"font={font},o=N,h=32,w=24",
            f"^FO80,80^A{font}N,32,24^FDHello 123^FS",
        )
    for just in [0, 1, 2]:
        add(
            f"fo-justify-{just}",
            "layout",
            "^FO",
            f"x=220,y=80,z={just}",
            f"^FO220,80,{just}" + text,
        )
    add("ft-baseline", "layout", "^FT", "x=80,y=100", "^FT80,100" + text)
    for cmd, value in [
        ("LH", "30,20"),
        ("LS", "20"),
        ("LT", "20"),
        ("PO", "I"),
        ("LR", "Y"),
        ("FW", "R"),
    ]:
        add(
            f"layout-{cmd}",
            "layout",
            "^" + cmd,
            value,
            f"^{cmd}{value}^FO80,80^FDABC^FS",
        )
    add(
        "field-reverse",
        "layout",
        "^FR",
        "reverse current field",
        "^FO60,60^GB240,100,100^FS^FO80,80^FR" + text,
    )
    for just in ["L", "C", "R", "J"]:
        add(
            f"block-{just}",
            "text",
            "^FB",
            f"w=220,lines=3,space=2,align={just},indent=0",
            f"^FO80,50^A0N,32,0^FB220,3,2,{just},0^FDOne two three four five^FS",
        )
    add(
        "block-indent",
        "text",
        "^FB",
        "indent=20",
        "^FO80,50^A0N,32,0^FB220,3,2,L,20^FDOne two three four five^FS",
    )
    add(
        "block-explicit-break",
        "text",
        "^FB",
        "explicit \\& break",
        "^FO80,50^A0N,32,0^FB220,3,0,L,0^FDOne\\&two^FS",
    )
    add(
        "field-hex",
        "text",
        "^FH",
        "indicator=_, bytes _41_42_43",
        "^FO80,80^A0N,32,0^FH_^FD_41_42_43^FS",
    )
    add(
        "variable-data",
        "text",
        "^FV",
        "literal field value",
        "^FO80,80^A0N,32,0^FVABC^FS",
    )
    for encoding in [0, 27, 28]:
        add(
            f"encoding-{encoding}",
            "text",
            "^CI",
            f"encoding={encoding}",
            f"^CI{encoding}^FO80,80^A0N,32,0^FDASCII 123^FS",
        )
    add(
        "utf8-accent",
        "text",
        "^CI",
        "encoding=28; UTF-8 é",
        "^CI28^FO80,80^A0N,32,0^FDCafé^FS",
    )
    for thickness in [1, 4, 60]:
        add(
            f"box-thickness-{thickness}",
            "shapes",
            "^GB",
            f"w=100,h=60,t={thickness},color=B,round=0",
            f"^FO80,80^GB100,60,{thickness},B,0^FS",
        )
    add("box-round", "shapes", "^GB", "round=4", "^FO80,80^GB100,60,4,B,4^FS")
    add(
        "box-white",
        "shapes",
        "^GB",
        "color=W",
        "^FO60,60^GB160,100,100^FS^FO80,80^GB100,60,4,W,0^FS",
    )
    for cmd, params in [
        ("GC", "80,3,B"),
        ("GE", "120,60,3,B"),
        ("GD", "120,60,3,B,R"),
        ("GD", "120,60,3,B,L"),
    ]:
        add(
            "shape-" + cmd + "-" + params[-1],
            "shapes",
            "^" + cmd,
            params,
            f"^FO80,80^{cmd}{params}^FS",
        )
    graphic = bytes.fromhex("FF818181818181FF")
    add(
        "graphic-hex",
        "graphics",
        "^GF",
        "A,8,8,1; raw hex",
        "^FO80,80^GFA,8,8,1," + graphic.hex().upper() + "^FS",
    )
    add(
        "graphic-binary",
        "graphics",
        "^GF",
        "B,8,8,1; ASCII binary bytes",
        "^FO80,80^GFB,8,8,1,AAAAAAAA^FS",
    )
    for encoding in ["B64", "Z64"]:
        payload = base64.b64encode(
            zlib.compress(graphic) if encoding == "Z64" else graphic
        ).decode()
        crc = binascii.crc_hqx(payload.encode(), 0)
        add(
            "graphic-" + encoding,
            "graphics",
            "^GF",
            f"A,8,8,1; {encoding}, CRC16",
            "^FO80,80^GFA,8,8,1,:" + encoding + ":" + payload + f":{crc:04X}^FS",
        )
    for ratio in [2, 3]:
        add(
            f"code39-ratio-{ratio}",
            "barcode-arguments",
            "^BY",
            f"w=2,ratio={ratio},height=60",
            f"^FO80,60^BY2,{ratio},60^B3N,N,60,N,N^FDABC123^FS",
        )
    for check in ["N", "Y"]:
        add(
            f"code39-check-{check}",
            "barcode-arguments",
            "^B3",
            f"o=N,check={check},h=60,readable=N",
            f"^FO80,60^BY2^B3N,{check},60,N,N^FDABC123^FS",
        )
    for interpretation, above in [("N", "N"), ("Y", "N"), ("Y", "Y")]:
        add(
            f"code128-text-{interpretation}{above}",
            "barcode-arguments",
            "^BC",
            f"h=60,interpretation={interpretation},above={above}",
            f"^FO80,80^BY2^BCN,60,{interpretation},{above},N,N^FDABC123^FS",
        )
    for orientation in ["R", "I", "B"]:
        add(
            f"code128-rotation-{orientation}",
            "barcode-arguments",
            "^BC",
            f"o={orientation},h=60",
            f"^FO250,80^BY2^BC{orientation},60,N,N^FDABC^FS",
        )
    for mode in ["N", "A"]:
        add(
            f"code128-mode-{mode}",
            "barcode-arguments",
            "^BC",
            f"mode={mode}",
            f"^FO80,60^BY2^BCN,60,N,N,N,{mode}^FD12345678^FS",
        )
    for model in [1, 2]:
        add(
            f"qr-model-{model}",
            "barcode-arguments",
            "^BQ",
            f"o=N,model={model},magnification=3,EC=L,mask=0",
            f"^FO80,60^BQN,{model},3,L,0^FDLA,HELLO123^FS",
        )
    for ec in ["L", "M", "Q", "H"]:
        add(
            f"qr-ec-{ec}",
            "barcode-arguments",
            "^BQ",
            f"model=2,magnification=3,EC={ec},mask=0",
            f"^FO80,60^BQN,2,3,{ec},0^FD{ec}A,HELLO123^FS",
        )
    for magnification in [2, 5]:
        add(
            f"qr-module-{magnification}",
            "barcode-arguments",
            "^BQ",
            f"magnification={magnification}",
            f"^FO80,60^BQN,2,{magnification},L,0^FDLA,HELLO123^FS",
        )
    for mask in [0, 3, 7]:
        add(
            f"qr-mask-{mask}",
            "barcode-arguments",
            "^BQ",
            f"mask={mask}",
            f"^FO80,60^BQN,2,3,L,{mask}^FDLA,HELLO123^FS",
        )
    for module in [2, 4]:
        add(
            f"datamatrix-module-{module}",
            "barcode-arguments",
            "^BX",
            f"o=N,module={module},quality=200",
            f"^FO80,60^BXN,{module},200^FDHELLO123^FS",
        )
    # The same probe is captured again last; disagreement invalidates the fresh set.
    repeat = dict(rows[0])
    repeat["name"] = "repeat-end"
    repeat["group"] = "repeatability"
    rows.append(repeat)
    return rows
