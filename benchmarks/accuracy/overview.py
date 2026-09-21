"""Index every accuracy corpus and verify the published case/image coverage."""

import argparse
import json
import os
from pathlib import Path
import re
import statistics


ROOT = "docs/benchmarks/accuracy"
SUITES = [
    ("accuracy", "Argument and archived barcode accuracy", "comparisons"),
    ("conformance", "Feature conformance", "comparisons/features"),
    ("external-zpl", "External examples", "comparisons/external"),
    ("layout-accuracy", "Font-free layout", "comparisons/layout"),
]
START = "<!-- argument-barcode-detail-start -->"
END = "<!-- argument-barcode-detail-end -->"


def case_page(suite, case):
    prefix = "" if suite == "accuracy" else suite + "-"
    return ROOT + "/comparisons/cases/" + prefix + case + ".md"


def rebase_links(text, old, new):
    def replace(match):
        target = match.group(1)
        if "://" in target or target.startswith("#"):
            return target
        return os.path.relpath(Path(old).parent / target, Path(new).parent)

    return re.sub(r"(?<=\]\()([^)]+)(?=\))", replace, text)


def table(headers, rows):
    def line(row):
        return "| " + " | ".join(str(v).replace("|", "/").replace("\n", " ") for v in row) + " |"
    return "\n".join([line(headers), line(["---"] * len(headers)), *[line(r) for r in rows]])


def load_suites(dest):
    suites = []
    for key, title, gallery in SUITES:
        data = json.loads((dest.parent / key / "results.json").read_text())
        comparisons = data if key == "accuracy" else json.loads((dest / gallery / "results.json").read_text())
        cases = data["cases"]
        rows = comparisons["results"]
        libraries = sorted({r["library"] for r in data["results"]})
        ids = [c.get("id", c["name"]) for c in cases]
        expected = {(cid, lib) for cid in ids for lib in libraries}
        actual = {(r["case"], r["library"]) for r in rows}
        if not libraries or len(ids) != len(set(ids)) or actual != expected or len(rows) != len(expected):
            raise ValueError("Incomplete or duplicate accuracy matrix: " + key)
        suites.append(dict(key=key, title=title, gallery=gallery, data=data, cases=cases, rows=rows, libraries=libraries))
    return suites


def score(row):
    value = "unscored" if row.get("score") is None else f"{row['score'] * 100:.2f}%"
    return value + (" · " + row["status"] if row["status"] != "rendered" else "")


def mean(rows):
    scores = [r["score"] for r in rows if r.get("score") is not None]
    return f"{statistics.mean(scores) * 100:.2f}% ({len(scores)})" if scores else "unscored (0)"


def compose(original, suites):
    if START in original:
        original = original.split(START, 1)[1].split(END, 1)[0].strip()
    original = original.replace("# Accuracy against a real Zebra printer", "## Argument and archived barcode details", 1)
    inventory, categories, details, relations = [], [], [], []
    libraries = sorted({lib for suite in suites for lib in suite["libraries"]})
    for suite in suites:
        key, rows, cases = suite["key"], suite["rows"], suite["cases"]
        groups = sorted({c["group"] for c in cases})
        target = "#argument-and-archived-barcode-details" if key == "accuracy" else suite["gallery"] + "/README.md"
        inventory.append([
            f"[{suite['title']}]({target})", len(cases), len(groups), len(rows),
            sum(r.get("score") is not None for r in rows), sum("iou" in r for r in rows),
            suite["data"]["measured_utc"],
        ])
        lookup = {(r["case"], r["library"]): r for r in rows}
        for group in groups:
            selected = [c for c in cases if c["group"] == group]
            ids = {c.get("id", c["name"]) for c in selected}
            group_rows = [r for r in rows if r["case"] in ids]
            categories.append([suite["title"], group, len(selected), *[
                mean([r for r in group_rows if r["library"] == lib]) if lib in suite["libraries"] else "N/A"
                for lib in libraries
            ]])
            if key != "accuracy":
                details += [f"### {suite['title']}: {group}", table(
                    ["Case", "Classification", *suite["libraries"]],
                    [[f"[{c['name']}]({os.path.relpath(case_page(key, c.get('id', c['name'])), ROOT)})",
                      c.get("validity", "captured"),
                      *[score(lookup[c.get("id", c["name"]), lib]) for lib in suite["libraries"]]]
                     for c in selected],
                )]
        for relation in suite["data"].get("relations", []):
            relations.append([suite["title"], relation["set"], relation["library"], relation["status"],
                              " · ".join(f"[{cid}]({os.path.relpath(case_page(key, cid), ROOT)})" for cid in relation["cases"])])
    text = [
        "# Accuracy against a real Zebra printer",
        "This overview includes every printer IoU comparison and image difference across all accuracy corpora. "
        "Each tested case has a page in [comparisons/cases](comparisons/cases/) with printer, renderer, and difference images or explicit failure/unscored evidence.",
        "## Measurement inventory",
        "Counts include failed, blank, excluded, and unavailable-reference cases. Scored attempts include failures scored zero; "
        "image differences count actual image comparisons, including blank-reference comparisons whose IoU is excluded from scored means. "
        "Labelary is a renderer against the same printer baseline, not an additional accuracy corpus.",
        table(["Corpus", "Cases", "Categories", "Attempts", "Scored attempts", "Image differences", "Measured UTC"], inventory),
        "## Browse by library",
        table(["Library", *[suite["title"] for suite in suites]], [
            [lib, *[f"[Compare images]({suite['gallery']}/libraries/{lib}.md)"
                    if lib in suite["libraries"] else "N/A" for suite in suites]]
            for lib in libraries
        ]),
        "## Every category: mean foreground IoU",
        "Each cell shows mean IoU and its scored denominator in parentheses. Corpora remain separate because their sampling overlaps. "
        "N/A means the renderer was not tested in that corpus; unscored means no nonblank printer baseline. "
        "The original heatmap and Overall metric below cover only the argument/barcode corpus, not all corpora.",
        table(["Corpus", "Category", "Cases", *libraries], categories),
        START, original.strip(), END,
        "## All other tested cases",
        "Values are foreground IoU against the printer. Case links open every renderer's preview, difference, and diagnostics. "
        "Unscored cases remain listed rather than disappearing from coverage.",
        *details,
        "## Metamorphic image-equality checks",
        "These compare thresholded renderer images between related inputs. They report equal, different, or inconclusive; "
        "they do not calculate printer IoU or produce printer-difference images. Every participating input links to its case page.",
        table(["Corpus", "Relation", "Library", "Result", "Cases"], relations),
        "Repeated printer captures are integrity controls, not additional accuracy samples. They must match before scoring. "
        "Invalid-input acceptance/rejection reports and parser/command-support inventories do not calculate image IoU.",
    ]
    return "\n\n".join(text) + "\n"


def verify(dest, suites, text):
    repo = dest.resolve().parents[2]
    obsolete = (dest / "comparisons/README.md").resolve()
    if obsolete.exists():
        raise ValueError("Obsolete comparison index: " + str(obsolete))
    markdown_files = list((repo / "docs").rglob("*.md"))
    if (repo / "README.md").is_file():
        markdown_files.append(repo / "README.md")
    for markdown in markdown_files:
        for target in re.findall(r"\]\(([^)]+)\)", markdown.read_text()):
            if target.split("#", 1)[0] == "https://github.com/codyps/zpl-comparison/blob/generated/" + ROOT + "/comparisons/README.md":
                raise ValueError("Link to obsolete comparison index: " + str(markdown))
            if "://" not in target and not target.startswith("#"):
                if (markdown.parent / target.split("#", 1)[0]).resolve() == obsolete:
                    raise ValueError("Link to obsolete comparison index: " + str(markdown))
    pages = {}
    for suite in suites:
        key = suite["key"]
        for row in suite["rows"]:
            page = case_page(key, row["case"])
            relative = os.path.relpath(page, ROOT)
            if relative not in text:
                raise ValueError("Accuracy overview omits case: " + page)
            if page not in pages:
                content = (repo / page).read_text()
                for target in re.findall(r"\]\(([^)]+)\)", content):
                    if "://" not in target and not target.startswith("#"):
                        path = (repo / page).parent / target.split("#", 1)[0]
                        if not path.exists():
                            raise ValueError("Case page has broken link: " + page + " -> " + target)
                pages[page] = content
            content = pages[page]
            if "## " + row["library"] + "\n" not in content:
                raise ValueError("Case page omits renderer: " + page + "/" + row["library"])
            prefix = row["case"] + "-" + row["library"]
            required = []
            if row["status"] in ("rendered", "blank"):
                required.append(f"docs/benchmarks/{key}/images/{prefix}.png")
            if "iou" in row:
                assets = ROOT if key == "accuracy" else ROOT + "/" + suite["gallery"]
                required.append(assets + "/images/" + prefix + "-diff.png")
            for image in required:
                if not (repo / image).is_file() or os.path.relpath(image, Path(page).parent) not in content:
                    raise ValueError("Case page missing comparison image: " + image)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    dest = args.destination
    suites = load_suites(dest)
    path = dest / "README.md"
    text = compose(path.read_text(), suites)
    if args.check:
        if path.read_text() != text:
            raise ValueError("Accuracy overview is out of date")
        verify(dest, suites, text)
    else:
        path.write_text(text)


if __name__ == "__main__":
    main()
