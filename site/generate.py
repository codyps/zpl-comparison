"""Publish comparison evidence as a static site; never execute measurements.

Input is the assembled report tree. Only explicitly selected evidence is copied;
internal scripts, Markdown reports and implementation directories are not shipped.
"""

import argparse
import hashlib
import html
import io
import json
import os
import re
import shutil
import statistics
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image, ImageChops

NAMES = {
    "codyps-zpl": "codyps/zpl",
    "labelize": "labelize",
    "forge": "zpl-forge",
    "go": "go-zpl",
    "ffi": "zpl-rs",
    "binarykits": "BinaryKits.Zpl",
    "zplr": "ZPLr",
    "labelary": "Labelary (service)",
    "toolchain": "zpl-toolchain",
    "builder": "zpl-builder",
    "python": "Python ZPL",
    "jszpl": "JSZPL",
}
SUITES = [
    ("accuracy", "ZD621 · arguments & barcodes", None, None),
    ("conformance", "ZD621 · feature tests", "features", "render-conformance"),
    ("external-zpl", "ZD621 · example labels", "external", "external-zpl"),
    ("layout-accuracy", "ZD621 · font-free layout", "layout", "layout-accuracy"),
    ("zq610-candidates", "ZQ610 Plus · renderer candidates", None, None),
]
E = lambda value: html.escape(str(value), quote=True)


def slug(value):
    return re.sub(r"[^a-zA-Z0-9_-]", "-", value)


def inline(text):
    """Escape evidence prose, retaining code and safe external source links."""
    text = E(
        text.replace(
            "No production font-fitting changes are part of this benchmark. ", ""
        ).replace(
            "Crates.io source is pinned by Cargo.lock;", "Pinned Crates.io source;"
        )
    )
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"\[([^\]]+)\]\((https?://[^ )]+)\)", r'<a href="\2">\1</a>', text)


def markdown_tables(text):
    """Read only maintained survey tables; prose/build instructions are excluded."""
    tables, current = [], []
    for line in text.splitlines() + [""]:
        if line.startswith("|"):
            cells = [part.strip() for part in line.strip("|").split("|")]
            if not all(re.fullmatch(r"[: -]+", cell) for cell in cells):
                current.append(cells)
        elif current:
            tables.append(current)
            current = []
    return tables


@lru_cache(maxsize=16384)
def ink_bounds(path):
    with Image.open(path) as raw:
        rgba = raw.convert("RGBA")
        image = Image.new("RGBA", rgba.size, "white")
        image.alpha_composite(rgba)
        rgb = image.convert("RGB")
        return ImageChops.difference(rgb, Image.new("RGB", rgb.size, "white")).getbbox()


def shared_bounds(paths):
    bounds = [b for path in paths if path for b in [ink_bounds(path)] if b]
    if not bounds:
        return (0, 0, 64, 64)
    return (
        min(b[0] for b in bounds) - 8,
        min(b[1] for b in bounds) - 8,
        max(b[2] for b in bounds) + 8,
        max(b[3] for b in bounds) + 8,
    )


def table(headers, rows, caption, kind=""):
    return (
        '<div class="table-wrap '
        + E(kind)
        + '" role="region" aria-label="'
        + E(caption)
        + '" tabindex="0"><table><caption>'
        + E(caption)
        + "</caption><thead><tr>"
        + "".join('<th scope="col">' + h + "</th>" for h in headers)
        + "</tr></thead><tbody>"
        + "".join(
            '<tr><th scope="row">'
            + row[0]
            + "</th>"
            + "".join("<td>" + c + "</td>" for c in row[1:])
            + "</tr>"
            for row in rows
        )
        + "</tbody></table></div>"
    )


def summary(rows):
    scores = [r["score"] for r in rows if r.get("score") is not None]
    return (statistics.mean(scores) if scores else None, len(scores), len(rows))


def heat(rows, href):
    score, n, total = summary(rows)
    if not total:
        href = href.split("#")[0] or "#main"
    label = (
        f"{score:.1%}"
        if score is not None
        else "Unscored"
        if total
        else "No observations"
    )
    color = f"hsl({round(score * 145)} 48% 88%)" if score is not None else "#edf0f3"
    return f'<a class="heat" style="background:{color}" href="{E(href)}"><strong>{label}</strong><small>{n}/{total} scored</small></a>'


class Site:
    def __init__(self, source, output):
        self.source, self.output = Path(source).resolve(), Path(output).resolve()
        if self.output == self.source or self.source.is_relative_to(self.output):
            raise ValueError("Output must not contain the input tree")
        if self.output.exists() and any(self.output.iterdir()):
            raise ValueError("Output directory must be empty (choose a new directory)")
        self.output.mkdir(parents=True, exist_ok=True)
        self.page = "index.html"
        self.assets = {}
        self.cases = []
        self.suites = []
        self.raw = {}
        self.focus_cache = {}

    def read(self, path):
        return json.loads((self.source / path).read_text())

    def href(self, path):
        return os.path.relpath(path, Path(self.page).parent)

    def link(self, path, label):
        return f'<a href="{E(self.href(path))}">{E(label)}</a>'

    def asset(self, path, required=True):
        if not path:
            return None
        src = (self.source / path).resolve()
        if not src.is_relative_to(self.source):
            raise ValueError("Evidence escapes input tree: " + str(path))
        if not src.is_file():
            if required:
                raise ValueError("Missing evidence: " + str(path))
            return None
        if str(src) not in self.assets:
            digest = hashlib.sha256(src.read_bytes()).hexdigest()
            target = "assets/" + digest + src.suffix.lower()
            dest = self.output / target
            dest.parent.mkdir(exist_ok=True)
            if not dest.exists():
                shutil.copyfile(src, dest)
            self.assets[str(src)] = target
        return self.assets[str(src)]

    def focused(self, asset, bounds):
        if not asset:
            return None
        key = (asset, bounds)
        if key not in self.focus_cache:
            with Image.open(self.output / asset) as raw:
                rgba = raw.convert("RGBA")
                canvas = Image.new(
                    "RGBA", (bounds[2] - bounds[0], bounds[3] - bounds[1]), "white"
                )
                canvas.paste(rgba, (-bounds[0], -bounds[1]), rgba)
                image = canvas.convert("RGB")
                image.thumbnail((1200, 800), Image.Resampling.NEAREST)
                encoded = io.BytesIO()
                image.save(encoded, format="PNG")
            data = encoded.getvalue()
            target = "assets/" + hashlib.sha256(data).hexdigest() + ".png"
            if not (self.output / target).exists():
                (self.output / target).write_bytes(data)
            self.focus_cache[key] = target
        return self.focus_cache[key]

    def focus_cases(self):
        for case in self.cases:
            originals = (
                [case["reference"]]
                + [r["image_asset"] for r in case["rows"]]
                + [r["diff_asset"] for r in case["rows"]]
            )
            bounds = shared_bounds([self.output / p for p in originals if p])
            case["reference_thumb"] = self.focused(case["reference"], bounds)
            for row in case["rows"]:
                row["thumb_asset"] = self.focused(row["image_asset"], bounds)
                row["diff_thumb"] = self.focused(row["diff_asset"], bounds)

    def image(self, path, label, thumb=None):
        if not path:
            return '<span class="muted">No image available</span>'
        controls = (
            f' data-focus="{E(self.href(thumb))}" data-full="{E(self.href(path))}"'
            if thumb and thumb != path
            else ""
        )
        return f'<a href="{E(self.href(path))}"><img loading="lazy"{controls} src="{E(self.href(thumb or path))}" alt="{E(label)}"></a>'

    def write(self, title, body, section="Measured comparisons", meta=""):
        category = self.page.startswith("categories/")
        library = self.page.startswith("libraries/")
        if "data-focus=" in body and "data-full-canvas" not in body + meta:
            body = (
                '<div class="view-controls"><label><input type="checkbox" data-full-canvas> Full canvas</label><span>Shared ink crop by default · click images for originals</span></div>'
                + body
            )
        nav = [
            ("index.html", "Overview"),
            ("categories.html", "Categories"),
            ("libraries.html", "Libraries"),
            ("cases.html", "ZPL documents"),
            ("examination.html", "Examined support"),
            ("methodology.html", "Methodology"),
        ]
        content = (
            '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>'
            + E(title)
            + ' · ZPL comparisons</title><link rel="stylesheet" href="'
            + self.href("style.css")
            + '"><script defer src="'
            + self.href("site.js")
            + '"></script></head><body'
            + (' class="category-page"' if category else ' class="library-page"' if library else '')
            + '><a class="skip" href="#main">Skip to content</a><header><a class="brand" href="'
            + self.href("index.html")
            + '">ZPL / comparisons</a><nav aria-label="Main navigation">'
            + "".join(
                self.link(p, label).replace('<a ', '<a class="nav-methodology" ', 1)
                if p == "methodology.html" else self.link(p, label)
                for p, label in nav
            )
            + '</nav></header><main id="main">'
            + ('' if category or library or not section else '<p class="eyebrow">' + E(section) + '</p>')
            + '<div class="page-heading"><h1>'
            + E(title)
            + '</h1>' + meta + '</div>'
            + body
            + "</main></body></html>"
        )
        dest = self.output / self.page
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)

    def load(self):
        for sid, title, comparison, corpus in SUITES:
            base = "docs/benchmarks/" + sid
            data = self.read(base + "/results.json")
            scored = (
                self.read(
                    "docs/benchmarks/accuracy/comparisons/"
                    + comparison
                    + "/results.json"
                )
                if comparison
                else data
            )
            self.raw[sid] = self.asset(base + "/results.json")
            if comparison:
                self.raw[sid + "-scores"] = self.asset(
                    "docs/benchmarks/accuracy/comparisons/"
                    + comparison
                    + "/results.json"
                )
            suite = {
                "id": sid,
                "title": title,
                "date": data.get("measured_utc", "Per-observation dates in evidence"),
                "cases": [],
            }
            lookup = {}
            for row in scored["results"]:
                key = (row["case"], row["library"])
                if key in lookup:
                    raise ValueError("Duplicate comparison " + str(key))
                lookup[key] = row
            expected = {(r["case"], r["library"]) for r in data["results"]}
            if set(lookup) != expected:
                raise ValueError(
                    "Comparison coverage differs from observations: " + sid
                )
            for c in data["cases"]:
                cid = c.get("id", c["name"])
                key = sid + "--" + slug(cid)
                source = c.get("zpl") or (
                    c.get("source")
                    if sid == "zq610-candidates"
                    else "test-data/" + corpus + "/" + c["file"]
                )
                reference = (
                    c.get("reference")
                    if not comparison
                    else "benchmarks/accuracy/"
                    + {
                        "features": "conformance",
                        "external": "external",
                        "layout": "layout",
                    }[comparison]
                    + "-reference/"
                    + cid
                    + ".png"
                )
                case = {
                    "id": cid,
                    "key": key,
                    "suite": sid,
                    "title": c["name"],
                    "group": c.get("group", "native-canvas"),
                    "description": c.get("purpose", c.get("arguments", "")),
                    "notes": c.get("notes", "").replace(
                        'Not certified for validity or printer fidelity. Canvas supplied by harness when omitted by source.', ""
                    ).strip(),
                    "commands": c.get(
                        "commands", [c["command"]] if "command" in c else []
                    ),
                    "source": self.asset(source),
                    "reference": self.asset(
                        reference,
                        required=bool(c.get("reference"))
                        or any(
                            "reference_ink" in r
                            for (name, _), r in lookup.items()
                            if name == cid
                        ),
                    ),
                    "rows": [],
                    "metadata": c,
                }
                preview_base = (
                    "docs/benchmarks/accuracy/comparisons/" + comparison
                    if comparison
                    else base
                )
                case["reference_thumb"] = self.asset(
                    preview_base + "/previews/" + cid + "-printer.png", required=False
                )
                if c.get("license") and corpus:
                    case["license"] = self.asset(
                        "test-data/" + corpus + "/" + c["license"]
                    )
                for (name, lib), row in lookup.items():
                    if name != cid:
                        continue
                    r = dict(row)
                    prefix = cid + "-" + lib
                    image = base + "/images/" + prefix + ".png"
                    assets = (
                        "docs/benchmarks/accuracy/comparisons/" + comparison
                        if comparison
                        else base
                    )
                    r["image_asset"] = (
                        self.asset(image)
                        if row["status"] in ("rendered", "blank")
                        else None
                    )
                    r["diff_asset"] = self.asset(
                        assets + "/images/" + prefix + "-diff.png",
                        required=row.get("iou") is not None,
                    )
                    r["thumb_asset"] = self.asset(
                        assets + "/previews/" + prefix + ".png", required=False
                    )
                    r["diff_thumb"] = self.asset(
                        assets + "/previews/" + prefix + "-diff.png", required=False
                    )
                    case["rows"].append(r)
                if not case["rows"]:
                    raise ValueError("Case has no observations: " + key)
                suite["cases"].append(case)
                self.cases.append(case)
            self.suites.append(suite)
        self.load_paired()
        if len({c["key"] for c in self.cases}) != len(self.cases):
            raise ValueError("Case URL collision")
        self.performance = (self.read("docs/benchmarks/results.json")
                            if (self.source / "docs/benchmarks/results.json").exists()
                            else {"timestamp_utc": "Not measured in this build", "results": [], "sizes": {}})
        self.invalid = self.read("docs/benchmarks/invalid/results.json")
        self.support = self.read("docs/benchmarks/command-support.json")
        self.libraries = sorted(
            {r["library"] for r in self.invalid["results"]}
            | set(self.support["commands"])
            | {r["library"] for c in self.cases for r in c["rows"]}
            | {r["library"] for r in self.performance["results"]}
        )

    def load_paired(self):
        base = "docs/benchmarks/zq610-plus"
        data = self.read(base + "/results.json")
        self.raw["paired"] = self.asset(base + "/results.json")
        self.raw["paired-manifest"] = self.asset(
            "references/zq610-plus-v1/manifest.json"
        )
        for printer in ("zq610", "zd621"):
            sid = "profile-" + printer
            self.raw[sid] = self.raw["paired"]
            suite = {
                "id": sid,
                "title": printer.upper() + " · codyps/zpl printer profile",
                "date": "Capture dates in evidence",
                "cases": [],
            }
            for name, result in data["cases"].items():
                m = result[printer]
                image_base = base + "/" + name + "/" + printer
                row = dict(
                    m,
                    library="codyps-zpl",
                    status="rendered" if "local_png_sha256" in m else "unavailable",
                    score=m.get("foreground_iou") if m.get("nonblank") else None,
                    missing=m.get("underpaint"),
                    extra=m.get("overpaint"),
                    dimensions_match=m.get("dimensions_equal"),
                )
                row.update(
                    image_asset=self.asset(image_base + "-local.png", required=False),
                    diff_asset=self.asset(image_base + "-diff.png", required=False),
                )
                case = {
                    "id": name,
                    "key": sid + "--" + slug(name),
                    "suite": sid,
                    "title": name,
                    "group": "printer-profile",
                    "description": "Printer-specific local rendering against the native capture.",
                    "notes": "Cross-printer common-region results are separate from full-canvas fidelity. Common region: "
                    + json.dumps(result["common_coordinate_region"], sort_keys=True),
                    "commands": [],
                    "source": self.asset(image_base + ".zpl"),
                    "reference": self.asset(image_base + ".png"),
                    "rows": [row],
                    "metadata": result,
                }
                suite["cases"].append(case)
                self.cases.append(case)
            suite["unavailable"] = data.get("unavailable", {})
            self.suites.append(suite)

    def case_link(self, case, label=None, lib=None):
        path = "cases/" + case["key"] + ".html"
        return (
            self.link(path, label or case["title"])
            if not lib
            else f'<a href="{E(self.href(path))}#{E(slug(lib))}">{E(label or case["title"])}</a>'
        )

    def result(self, row):
        score = row.get("score")
        label = f"{score:.2%} IoU" if score is not None else "Unscored"
        return E(
            label
            + " · "
            + row.get("comparison_status", row["status"])
            + (" · exact" if row.get("exact") and score is not None else "")
        )

    def case_table(self, cases, library=None):
        rows = []
        for c in cases:
            observations = [
                r for r in c["rows"] if library is None or r["library"] == library
            ]
            for r in observations:
                lib = r["library"]
                rows.append(
                    [
                        self.case_link(c, lib=lib),
                        E(c["group"]),
                        self.link(
                            "libraries/" + slug(lib) + ".html", NAMES.get(lib, lib)
                        ),
                        self.result(r),
                        self.image(
                            c["reference"],
                            c["title"] + " printer",
                            c.get("reference_thumb"),
                        ),
                        self.image(
                            r["image_asset"],
                            NAMES.get(lib, lib) + " render",
                            r.get("thumb_asset"),
                        ),
                        self.image(
                            r["diff_asset"],
                            NAMES.get(lib, lib) + " difference",
                            r.get("diff_thumb"),
                        ),
                    ]
                )
        return table(
            [
                "ZPL document / result",
                "Category",
                "Library",
                "Measurement",
                "Printer",
                "Render",
                "Difference",
            ],
            rows,
            "Image comparisons",
        )

    def comparison_matrix(self, cases, libraries):
        present = {r["library"] for c in cases for r in c["rows"]}
        libraries = [lib for lib in libraries if lib in present]
        headers = ["ZPL case / printer"] + [
            f'<span id="{slug(lib)}">'
            + self.link("libraries/" + slug(lib) + ".html", NAMES.get(lib, lib))
            + "</span>"
            for lib in libraries
        ]
        rows = []
        for case in cases:
            row = [
                self.case_link(case)
                + "<small>"
                + E(case["group"])
                + "</small>"
                + self.image(
                    case["reference"],
                    case["title"] + " printer",
                    case.get("reference_thumb"),
                )
            ]
            observations = {r["library"]: r for r in case["rows"]}
            for lib in libraries:
                r = observations.get(lib)
                if not r:
                    row.append('<span class="muted">No observation</span>')
                    continue
                score = r.get("score")
                color = (
                    f"hsl({round(score * 145)} 48% 88%)"
                    if score is not None
                    else "#edf0f3"
                )
                path = self.href("cases/" + case["key"] + ".html") + "#" + slug(lib)
                label = f"{score:.2%} IoU" if score is not None else "Unscored"
                status = r.get("comparison_status", r["status"]) + (
                    " · exact" if r.get("exact") and score is not None else ""
                )
                preview = (
                    self.image(
                        r["diff_asset"],
                        case["title"] + " · " + NAMES.get(lib, lib) + " difference",
                        r.get("diff_thumb"),
                    )
                    if r["diff_asset"]
                    else '<span class="muted">Difference unavailable</span>'
                )
                row.append(
                    f'<a class="matrix-score" style="background:{color}" href="{E(path)}">{E(label)}</a><small>'
                    + E(status)
                    + "</small>"
                    + preview
                    + self.case_link(case, "Inspect result", lib)
                )
            rows.append(row)
        return (
            '<div class="matrix-toolbar"><label class="filter">Find a case <input type="search" data-filter placeholder="Name or category"></label><span data-count aria-live="polite"></span><label><input type="checkbox" data-full-canvas> Full canvas</label></div>'
            + table(
                headers,
                rows,
                "Scores and differences · cases × libraries",
                "comparison-matrix",
            )
        )

    def case_pages(self):
        for c in self.cases:
            self.page = "cases/" + c["key"] + ".html"
            body = (
                "<p>"
                + self.link(
                    "categories/" + c["suite"] + ".html",
                    "All results in this comparison",
                )
                + " · "
                + self.link(c["source"], "Download exact ZPL")
                + "</p><p>"
                + E(c["description"])
                + "</p><p>"
                + E(c["notes"])
                + "</p>"
            )
            original = c["metadata"].get("source", "")
            if isinstance(original, str) and urlsplit(original).scheme in (
                "http",
                "https",
            ):
                body += (
                    '<p><a href="'
                    + E(original)
                    + '">Original source & revision</a></p>'
                )
            if c.get("license"):
                body += "<p>" + self.link(c["license"], "Source license") + "</p>"
            body += (
                "<p>Commands: "
                + E(", ".join(c["commands"]) or "See exact ZPL")
                + "</p><p>Black: shared ink; magenta: printer-only ink; cyan: library-only ink. Images open at original resolution.</p>"
            )
            body += (
                "<p>Jump to library: "
                + " · ".join(
                    f'<a href="#{E(slug(r["library"]))}">{E(NAMES.get(r["library"], r["library"]))}</a>'
                    for r in c["rows"]
                )
                + "</p>"
            )
            if len(c["rows"]) > 1:
                body += (
                    '<section data-output-comparison><h2>Compare all outputs</h2>'
                    + ('<p data-diff-control hidden><label><input type="checkbox" data-contact-diffs aria-controls="all-outputs"> Show differences from printer preview</label></p>'
                       if any(r['diff_asset'] for r in c['rows']) else '')
                    + '<div class="contact-sheet" id="all-outputs"><figure>'
                    + self.image(
                        c["reference"], "Printer reference", c.get("reference_thumb")
                    )
                    + "<figcaption>Printer reference</figcaption></figure>"
                )
                for observation in c["rows"]:
                    lib = observation["library"]
                    body += (
                        '<figure><div data-render-view>'
                        + self.image(
                            observation["image_asset"],
                            NAMES.get(lib, lib) + " render",
                            observation.get("thumb_asset"),
                        )
                        + '</div><div data-diff-view hidden>'
                        + (self.image(
                            observation["diff_asset"],
                            NAMES.get(lib, lib) + " difference from printer preview",
                            observation.get("diff_thumb"),
                        ) if observation["diff_asset"] else '<span class="muted">No difference image available</span>')
                        + '</div><figcaption><a href="#'
                        + slug(lib)
                        + '">'
                        + E(NAMES.get(lib, lib))
                        + "</a><br>"
                        + self.result(observation)
                        + "</figcaption></figure>"
                    )
                body += "</div></section>"
            for r in c["rows"]:
                lib = r["library"]
                body += (
                    f'<section id="{E(slug(lib))}"><h2>'
                    + self.link("libraries/" + slug(lib) + ".html", NAMES.get(lib, lib))
                    + "</h2><p>"
                    + self.result(r)
                    + "</p>"
                )
                body += (
                    '<div class="panels">'
                    + "".join(
                        "<figure>"
                        + self.image(p, label, thumb)
                        + "<figcaption>"
                        + label
                        + "</figcaption></figure>"
                        for p, label, thumb in [
                            (
                                c["reference"],
                                "Printer reference",
                                c.get("reference_thumb"),
                            ),
                            (r["image_asset"], "Library render", r.get("thumb_asset")),
                            (r["diff_asset"], "Difference", r.get("diff_thumb")),
                        ]
                    )
                    + "</div>"
                )
                if c["reference"] and r["image_asset"]:
                    body += (
                        '<details class="overlay"><summary>Overlay at native dimensions</summary><p>Both images share the top-left origin. Scroll to inspect; no rescaling or alignment.</p><label>Library opacity <input type="range" min="0" max="100" value="50"><output>50%</output></label><div class="overlay-scroll"><div class="overlay-images"><img src="'
                        + E(self.href(c["reference"]))
                        + '" loading="lazy" alt="Printer reference"><img class="overlay-render" src="'
                        + E(self.href(r["image_asset"]))
                        + '" loading="lazy" alt="Library overlay"></div></div></details>'
                    )
                fields = {
                    k: r[k]
                    for k in (
                        "output_dimensions",
                        "requested_dimensions",
                        "dimensions_match",
                        "missing",
                        "extra",
                        "reference_ink",
                        "observed_utc",
                        "profile",
                        "comparison_diagnostic",
                    )
                    if k in r
                }
                body += (
                    "<details><summary>Measurement details</summary><dl>"
                    + "".join(
                        "<dt>" + E(k.replace("_", " ")) + "</dt><dd>" + E(v) + "</dd>"
                        for k, v in fields.items()
                    )
                    + "</dl></details>"
                )
                if r.get("diagnostic") or r.get("error"):
                    body += (
                        "<details><summary>Observation diagnostic</summary><pre>"
                        + E(r.get("error") or r["diagnostic"])
                        + "</pre></details>"
                    )
                body += "</section>"
            body += (
                "<details><summary>ZPL source</summary><pre>"
                + E((self.output / c["source"]).read_text(errors="replace"))
                + "</pre></details><p>"
                + self.link(
                    self.raw.get(c["suite"] + "-scores", self.raw[c["suite"]]),
                    "Measurements & provenance (JSON)",
                )
                + "</p>"
            )
            self.write(c["title"], body)

    def indexes(self):
        self.page = "index.html"
        body = ""
        body += (
            '<div class="stats"><div><strong>'
            + str(len(self.libraries))
            + "</strong> implementations</div><div><strong>"
            + str(len(self.cases))
            + "</strong> documents & profiles</div><div><strong>"
            + str(len(self.suites))
            + "</strong> image comparison sets</div></div><p>Mean foreground intersection-over-union (IoU), higher is better. Each cell shows scored / observed comparisons. Gray means unscored. Separate printer profiles and test populations are not interchangeable.</p>"
        )
        libraries = [
            lib
            for lib in self.libraries
            if any(r["library"] == lib for c in self.cases for r in c["rows"])
        ]
        body += table(
            ["Comparison"]
            + [
                self.link("libraries/" + slug(lib) + ".html", NAMES.get(lib, lib))
                for lib in libraries
            ],
            [
                [self.link("categories/" + s["id"] + ".html", s["title"])]
                + [
                    heat(
                        [
                            r
                            for c in s["cases"]
                            for r in c["rows"]
                            if r["library"] == lib
                        ],
                        self.href("categories/" + s["id"] + ".html") + "#" + slug(lib),
                    )
                    for lib in libraries
                ]
                for s in self.suites
            ],
            "Quantitative rendering quality",
        )
        body += (
            '<h2>Explore the image evidence</h2><div class="panels">'
            + "".join(
                "<figure>"
                + self.case_link(c)
                + self.image(
                    c["reference"], c["title"] + " printer", c.get("reference_thumb")
                )
                + "<figcaption>"
                + E(c["group"])
                + "</figcaption></figure>"
                for c in [s["cases"][0] for s in self.suites[:3]]
            )
            + "</div>"
        )
        body += (
            '<div class="cards">'
            + "".join(
                "<article><h2>"
                + self.link(path, title)
                + "</h2><p>"
                + text
                + "</p></article>"
                for path, title, text in [
                    (
                        "cases.html",
                        "Inspect a ZPL document",
                        "Printer, library and difference images, with an interactive overlay.",
                    ),
                    (
                        "categories/performance.html",
                        "Speed, memory & size",
                        "Compare the same workload across implementations.",
                    ),
                    (
                        "categories/invalid.html",
                        "Invalid-input behavior",
                        "Rejection, acceptance and recovery with valid controls.",
                    ),
                    (
                        "examination.html",
                        "Examined support",
                        "Source and catalog observations, kept outside the numerical quality scores.",
                    ),
                ]
            )
            + "</div>"
        )
        self.write("Compare ZPL implementations", body, section="")
        self.page = "categories.html"
        self.write(
            "Comparison categories",
            '<div class="cards">'
            + "".join(
                "<article><h2>"
                + self.link("categories/" + s["id"] + ".html", s["title"])
                + "</h2><p>"
                + str(len(s["cases"]))
                + " documents</p></article>"
                for s in self.suites
            )
            + "<article><h2>"
            + self.link("categories/performance.html", "Speed, memory & size")
            + "</h2></article><article><h2>"
            + self.link("categories/invalid.html", "Invalid-input behavior")
            + "</h2></article></div>",
        )
        self.page = "cases.html"
        rows = [
            [
                self.case_link(c),
                self.link("categories/" + c["suite"] + ".html", c["suite"]),
                E(c["group"]),
                E(" ".join(c["commands"])),
                self.image(
                    c["reference"], c["title"] + " printer", c.get("reference_thumb")
                ),
            ]
            for c in self.cases
        ]
        self.write(
            "ZPL documents",
            '<p>Each document belongs to a specific comparison and printer profile. Filter by name, category or command.</p><label class="filter">Find a document <input type="search" data-filter placeholder="e.g. barcode, ^BQ, layout"></label><p data-count aria-live="polite"></p>'
            + table(
                [
                    "Document / results",
                    "Comparison",
                    "Category",
                    "Commands",
                    "Printer preview",
                ],
                rows,
                "Documents and printer references",
            ),
        )
        for s in self.suites:
            self.page = "categories/" + s["id"] + ".html"
            meta = (
                '<div class="category-meta">'
                + self.link(self.raw[s["id"]], "Evidence (JSON)")
                + '</div>'
            )
            body = self.comparison_matrix(s["cases"], libraries)
            if s.get("unavailable"):
                body += (
                    "<h2>Unavailable captures</h2><pre>"
                    + E(json.dumps(s["unavailable"], indent=2))
                    + "</pre>"
                )
            self.write(s["title"], body, meta=meta)
        self.page = "libraries.html"
        self.write(
            "Implementations",
            '<div class="cards">'
            + "".join(
                "<article><h2>"
                + self.link("libraries/" + slug(lib) + ".html", NAMES.get(lib, lib))
                + "</h2></article>"
                for lib in self.libraries
            )
            + "</div>",
        )
        for lib in self.libraries:
            self.page = "libraries/" + slug(lib) + ".html"
            meta = (
                '<div class="library-links">'
                + self.link("examination.html", "Examined support")
                + self.link("categories/performance.html", "Performance")
                + self.link("categories/invalid.html", "Invalid inputs")
                + '<label><input type="checkbox" data-full-canvas> Full canvas</label>'
                + '</div>'
            )
            body = ""
            for s in self.suites:
                rows = [r for c in s["cases"] for r in c["rows"] if r["library"] == lib]
                if rows:
                    body += (
                        '<div class="library-section-heading"><h2>'
                        + self.link("categories/" + s["id"] + ".html", s["title"])
                        + "</h2>"
                        + heat(
                            rows,
                            self.href("categories/" + s["id"] + ".html")
                            + "#"
                            + slug(lib),
                        )
                        + "</div>"
                        + self.case_table(s["cases"], lib)
                    )
            if not any(r["library"] == lib for c in self.cases for r in c["rows"]):
                body += "<p>No printer-fidelity observations in these corpora. Parser and generator capabilities are separate from raster rendering.</p>"
            self.write(NAMES.get(lib, lib), body, meta=meta)

    def other_pages(self):
        self.page = "categories/performance.html"
        data = self.performance
        evidence = self.asset("docs/benchmarks/results.json", required=False)
        body = (
            "<p>Observed: "
            + E(data["timestamp_utc"])
            + ". Timings are measured on the recorded host. Successful API calls do not establish equivalent output or printer fidelity.</p><p>"
            + (self.link(evidence, "Samples, host, output checks & versions (JSON)") if evidence else "Performance is collected in trusted CI runs; this preview has no timing measurements.")
            + "</p>"
        )
        for mode, title in [
            ("parse", "Parsing"),
            ("png", "PNG rendering"),
            ("generate", "ZPL generation"),
        ]:
            rows = []
            for r in data["results"]:
                if r["mode"] != mode:
                    continue
                label = (
                    f"{r['median_ns'] / 1e6:.4f} ms"
                    if r["status"] == "ok"
                    else r["status"]
                )
                sample = self.asset(
                    "docs/benchmarks/samples/"
                    + r["library"]
                    + "-"
                    + mode
                    + "-"
                    + r["fixture"]
                    + (".png" if mode == "png" else ".txt"),
                    required=False,
                )
                preview = (
                    self.image(sample, r["library"] + " " + r["fixture"])
                    if mode == "png"
                    else self.link(sample, "Generated ZPL")
                    if sample
                    else "Not applicable"
                )
                rows.append(
                    [
                        self.link(
                            "libraries/" + slug(r["library"]) + ".html",
                            NAMES.get(r["library"], r["library"]),
                        ),
                        E(r["fixture"]),
                        E(label),
                        E(
                            f"{r['peak_rss_bytes'] / 1048576:.2f} MiB"
                            if r.get("peak_rss_bytes") is not None
                            else "Unavailable"
                        ),
                        preview,
                    ]
                )
            if not rows:
                continue
            chart = self.asset("docs/benchmarks/" + mode + ".svg", required=False)
            body += (
                "<h2>"
                + title
                + '</h2><div class="chart">'
                + (self.image(chart, title + " timing chart") if chart else "")
                + "</div>"
                + table(
                    [
                        "Library",
                        "Workload",
                        "Median duration",
                        "Peak process RSS",
                        "Output sample",
                    ],
                    rows,
                    title + " observations",
                )
            )
        body += "<h2>Deployment size</h2>" + table(
            ["Library", "Source bytes", "Artifact bytes"],
            [
                [
                    self.link("libraries/" + slug(lib) + ".html", NAMES.get(lib, lib)),
                    E(r.get("bytes", "Unavailable")),
                    E(r.get("artifact_bytes", "Unavailable")),
                ]
                for lib, r in data["sizes"].items()
            ],
            "Source and artifact sizes",
        )
        self.write("Speed, memory & size", body)
        self.page = "categories/invalid.html"
        evidence = self.asset("docs/benchmarks/invalid/results.json")
        body = (
            "<p>Observed: "
            + E(self.invalid["measured_utc"])
            + ". Acceptance, rejection and recovery depend on the API contract. A rejection is not a printer-fidelity score. Each invalid input has a valid control.</p><p>"
            + self.link(evidence, "Repeated outcomes & diagnostics (JSON)")
            + "</p>"
        )
        for c in self.invalid["cases"]:
            body += (
                '<h2 id="'
                + slug(c["id"])
                + '">'
                + E(c["id"])
                + "</h2><p>"
                + E(c["reason"])
                + "</p><p>"
                + E(c["caveat"])
                + "</p>"
            )
            for variant in ("control", "invalid"):
                source = self.asset("test-data/invalid-zpl/" + c[variant]["file"])
                body += (
                    "<p>" + self.link(source, variant.capitalize() + " ZPL") + "</p>"
                )
            body += table(
                [
                    "Library",
                    "API",
                    "Outcome",
                    "Control observations",
                    "Invalid observations",
                ],
                [
                    [
                        self.link(
                            "libraries/" + slug(r["library"]) + ".html",
                            NAMES.get(r["library"], r["library"]),
                        ),
                        E(r["mode"]),
                        E(r["outcome"]),
                        E(", ".join(x["status"] for x in r["control"])),
                        E(", ".join(x["status"] for x in r["invalid"])),
                    ]
                    for r in self.invalid["results"]
                    if r["case"] == c["id"]
                ],
                "Invalid input: " + c["id"],
            )
        self.write("Invalid-input behavior", body)
        self.page = "examination.html"
        body = '<p class="intro">Source examination and upstream claims. These findings are not reproducible pixel measurements and never contribute to the quantitative heatmap.</p><p>Entries refer to the versions linked in the evidence. They may describe partial argument handling. Missing evidence is not proof of absence.</p>'
        body += "<dl><dt>D</dt><dd>Explicit parser or render handler; not proof of fidelity.</dd><dt>I</dt><dd>Recognized but skipped or stored without the relevant raster effect.</dd><dt>F</dt><dd>Byte framing only; no renderer handler identified for codyps/zpl.</dd><dt>T</dt><dd>Command specification; no pixel renderer implied.</dd><dt>E</dt><dd>Typed generator emission path.</dd><dt>S / P / U / N</dt><dd>Upstream catalog: supported / partial / unsupported / non-rendering.</dd><dt>?</dt><dd>No explicit evidence found in the examined entry points.</dd></dl>"
        libs = list(self.support["commands"])
        commands = sorted(
            {
                line.split("\t")[0]
                for line in (self.source / "docs/zpl-command-index.tsv")
                .read_text()
                .splitlines()
                if line.startswith(("^", "~"))
            }
            | set().union(*(set(d) for d in self.support["commands"].values()))
        )
        rows = []
        for command in commands:
            cells = [
                E(command),
                E(", ".join(self.support.get("parameter_keys", {}).get(command, []))),
            ]
            for lib in libs:
                finding = self.support["commands"][lib].get(command)
                url = finding.get("source", "") if finding else ""
                # Only validated external evidence URLs are made clickable.
                if finding and urlsplit(url).scheme in ("http", "https"):
                    cells.append(
                        '<a href="' + E(url) + '">' + E(finding["status"]) + "</a>"
                    )
                else:
                    cells.append(
                        E(
                            finding["status"]
                            if finding
                            else "F"
                            if lib == "codyps-zpl"
                            else "?"
                        )
                    )
            rows.append(cells)
        body += table(
            ["Command", "Reference parameter names"]
            + [
                self.link("libraries/" + slug(lib) + ".html", NAMES.get(lib, lib))
                for lib in libs
            ],
            rows,
            "Examined command support, not measured quality",
        )
        # The maintained argument table is examination evidence, not numerical data.
        argument_text = (
            self.source / "docs/benchmarks/argument-support.md"
        ).read_text()
        lines = [line for line in argument_text.splitlines() if line.startswith("|")]
        first_table = []
        for line in lines[2:]:
            cells = [part.strip() for part in line.strip("|").split("|")]
            if len(cells) != 3:
                break
            first_table.append([inline(v) for v in cells])
        body += (
            "<h2>Examined argument limitations</h2><p>Maintained observations for the pinned versions; statements about examples are not additional measurements.</p>"
            + table(
                ["Library / API", "Position, text & graphics", "Barcode limits"],
                first_table,
                "Argument-level examination",
            )
        )
        body += "<h2>Capabilities and selection survey</h2><p>Surveyed 2026-09-18. Parser, renderer and generator APIs do different work. Popularity is a dated snapshot, not a quality score.</p>"
        for survey in markdown_tables(
            (self.source / "docs/benchmarks/capabilities.md").read_text()
        ):
            body += table(
                [inline(cell) for cell in survey[0]],
                [[inline(cell) for cell in row] for row in survey[1:]],
                "Examined capabilities and dated repository observations",
            )
        body += (
            "<p>"
            + self.link(
                self.asset("docs/benchmarks/command-support.json"),
                "Source inventory and pinned revisions (JSON)",
            )
            + "</p>"
        )
        self.write(
            "Examined support",
            body,
            section="Qualitative evidence · source examination",
        )
        self.page = "methodology.html"
        self.write(
            "Reading the results",
            """<p>These pages present saved observations, not a new measurement run. Each comparison links its original measurement document, including versions, capture dates and provenance. Local library observations and saved service responses may have different dates.</p>
<h2>What the heatmap means</h2><p>Foreground IoU is shared black pixels divided by the union of black pixels, using a threshold of 128. A score of 100% means identical ink; “exact” additionally requires matching dimensions. Means weight each scored case equally within one comparison. The denominator is the number of recorded attempts, including unscored observations. Scores from different corpora or printer profiles should not be treated as one overall ranking.</p>
<h2>Failures and unscored results</h2><p>In the four ZD621 corpora, failed renders with a nonblank printer reference contribute zero. Missing or blank references are unscored. ZQ610 candidate comparisons require identical native dimensions: canvas mismatches and failed or uncaptured renders remain unscored. Blank diagnostic cases never count as positive accuracy evidence. Inspect coverage alongside the mean; a high mean over few successful cases is not broad support.</p>
<h2>Image comparison</h2><p>The ZD621 corpora compare at the original origin on a white canvas large enough for both images; they do not resize or align ink. ZQ610 candidate and printer-profile comparisons use native canvases. The paired-printer common coordinate region is a separate diagnostic, not full-canvas equality. The opacity viewer places both originals at the same top-left origin without resizing. Side-by-side previews fit their panels. Previews crop all four blank margins to the union of ink across the reference, renders and differences, with an eight-pixel margin. Every image for a case uses the same bounds, including displaced or extra ink. Full canvas restores the uncropped view; metrics always use the full canvases. Click an image to inspect its original pixels.</p><p>Difference colors: black or dark gray is shared ink, magenta is missing ink, cyan is extra ink, and white is background. The overlay is a visual aid; it does not change the recorded score.</p>
<h2>Scope and limitations</h2><p>These finite probes do not establish exhaustive command, argument or firmware compatibility. Printer previews are references for specified devices and capture sessions, not physical print scans. Native-default candidates and a configured printer profile are distinct comparisons. Speed measurements describe the recorded host and workload; parser ASTs, generated labels and renderer outputs need not be semantically equivalent.</p>
<h2>Two kinds of evidence</h2><p>Measured comparisons derive from retained inputs, observations and explicit metrics. Examined support consists of source review, catalog claims and maintained argument notes. It is kept separate and is never converted into a quantitative quality score.</p>"""
            + "<h2>Evidence downloads</h2><ul>"
            + "".join(
                "<li>" + self.link(path, key + " · JSON") + "</li>"
                for key, path in self.raw.items()
            )
            + "</ul>",
        )

    def generate(self):
        self.load()
        self.focus_cases()
        for name, target in [("style.css", "style.css"), ("site.js", "site.js")]:
            shutil.copyfile(Path(__file__).parent / name, self.output / target)
        self.case_pages()
        self.indexes()
        self.other_pages()
        (self.output / ".nojekyll").touch()
        validate(self.output)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids = [], set()
        self.anchors = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.anchors.append(attrs["href"])
        if "id" in attrs:
            if attrs["id"] in self.ids:
                raise ValueError("Duplicate HTML id: " + attrs["id"])
            self.ids.add(attrs["id"])
        for name in ("href", "src"):
            if attrs.get(name):
                self.links.append(attrs[name])


def validate(root):
    root = Path(root).resolve()
    documents = {}
    for path in root.rglob("*.html"):
        parser = Links()
        parser.feed(path.read_text())
        methodology_links = [href for href in parser.anchors
                             if unquote(urlsplit(href).path).rsplit("/", 1)[-1] == "methodology.html"]
        if len(methodology_links) > 1:
            raise ValueError(f"Duplicate methodology links: {path.relative_to(root)}")
        documents[path] = parser
    for path, parser in documents.items():
        for link in parser.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not target.is_relative_to(root) or not target.is_file():
                raise ValueError(
                    f"Broken local link: {path.relative_to(root)} -> {link}"
                )
            if (
                url.fragment
                and target in documents
                and unquote(url.fragment) not in documents[target].ids
            ):
                raise ValueError(f"Broken fragment: {path.relative_to(root)} -> {link}")
    if list(root.rglob("*.md")):
        raise ValueError("Markdown must not be published")
    print(f"Validated {len(documents)} HTML pages and all local links/images")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("bazel-bin/reports"))
    parser.add_argument("--output", type=Path, default=Path("_site"))
    args = parser.parse_args()
    Site(args.input, args.output).generate()
