#!/usr/bin/env python3
"""Extract source evidence, not a claim that finding a command proves full support.
Sources are pinned in sources.lock.json / Cargo.lock. See generated legend.
"""

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
from report import NAMES, table  # noqa: E402


def main():
    metadata = json.loads((ROOT / "_work/cargo-metadata.json").read_text())
    packages = {
        p["name"]: Path(p["manifest_path"]).parent for p in metadata["packages"]
    }
    locks = json.loads((ROOT / "sources.lock.json").read_text())
    index = [
        line.split("\t")
        for line in (REPO / "docs/zpl-command-index.tsv").read_text().splitlines()
        if line.startswith(("^", "~"))
    ]
    evidence = {
        n: {}
        for n in [
            "codyps-zpl",
            "toolchain",
            "labelize",
            "forge",
            "go",
            "ffi",
            "binarykits",
            "zplr",
            "builder",
            "python",
            "jszpl",
            "labelary",
        ]
    }

    def link(path, line, repo=None, crate=None):
        if path.is_relative_to(ROOT / "_work/zpl"):
            repo = "zpl"
        if repo:
            relative = path.relative_to(ROOT / "_work" / repo)
            return f"{locks[repo]['url']}/blob/{locks[repo]['rev']}/{relative}#L{line}"
        if crate:
            relative = path.relative_to(packages[crate])
            version = next(
                p["version"] for p in metadata["packages"] if p["name"] == crate
            )
            return f"https://docs.rs/crate/{crate}/{version}/source/{relative}#{line}"
        return f"../../{path.relative_to(REPO)}#L{line}"

    def add(name, command, status, path, line, **kw):
        if command.startswith("^A") and command not in ["^A@"]:
            command = "^A"
        evidence[name][command] = {"status": status, "source": link(path, line, **kw)}

    def literals(name, paths, status, **kw):
        for path in paths:
            for i, line in enumerate(path.read_text().splitlines(), 1):
                if line.lstrip().startswith(("//", "///", "//!", "#", "*")):
                    continue
                for command in re.findall(
                    r"[\^~](?:A@|[A-Z][A-Z0-9]|A(?=[^A-Z0-9@]))", line
                ):
                    add(name, command, status, path, i, **kw)

    zpl_source = ROOT / "_work/zpl/zpl/src/render/mod.rs"
    in_dispatch = False
    for i, line in enumerate(zpl_source.read_text().splitlines(), 1):
        if line == "            match name {":
            in_dispatch = True
            continue
        if not in_dispatch:
            continue
        if line == "            }":
            break
        if re.match(r' {16}"[A-Z0-9]{2}"', line) and "=>" in line:
            for command in re.findall(r'"([A-Z][A-Z0-9])"', line.split("=>")[0]):
                add("codyps-zpl", "~DG" if command == "DG" else "^" + command, "D", zpl_source, i)
                if command in {"CC", "CD", "CT"}:
                    add("codyps-zpl", "~" + command, "D", zpl_source, i)
        if line.startswith("                n if n.starts_with('A') =>"):
            add("codyps-zpl", "^A", "D", zpl_source, i)
    barcode = ROOT / "_work/zpl/zpl/src/render/barcode.rs"
    in_supported = False
    for i, line in enumerate(barcode.read_text().splitlines(), 1):
        if line.startswith("pub(super) fn supported"):
            in_supported = True
        if not in_supported:
            continue
        if line == "}":
            break
        for command in re.findall(r'"(B[A-Z0-9])"', line):
            add("codyps-zpl", "^" + command, "D", barcode, i)
    # The toolchain's command specification is distinct from heuristic parse_str.
    params = {}
    descriptions = {}
    for path in sorted((ROOT / "_work/zpl-toolchain/spec/commands").glob("*.jsonc")):
        source = path.read_text()
        try:
            spec = json.loads(source)
        except json.JSONDecodeError:
            # Only full-line JSONC comments are stripped, never text inside strings.
            try:
                spec = json.loads(
                    "\n".join(
                        line
                        for line in source.splitlines()
                        if not line.lstrip().startswith("//")
                    )
                )
            except json.JSONDecodeError:
                continue
        for item in spec.get("commands", []):
            for code in item.get("codes", []):
                add("toolchain", code, "T", path, 1, repo="zpl-toolchain")
                params[code] = item.get("signature", {}).get("params", [])
                descriptions[code] = {
                    "name": item.get("name", code),
                    "description": item.get("docs", ""),
                }
    label = packages["labelize"] / "src/parsers/zpl_parser.rs"
    for i, line in enumerate(label.read_text().splitlines(), 1):
        for cmd in re.findall(r'starts_with\("([\^~][A-Z0-9@]+)"', line):
            add("labelize", cmd, "D", label, i, crate="labelize")
    for cmd in ["^XA", "^XZ"]:
        add("labelize", cmd, "D", label, 59, crate="labelize")
    for cmd in ["^SN", "^SF"]:
        add("labelize", cmd, "I", label, 413, crate="labelize")
    forge = packages["zpl-forge"] / "src/ast/parser/standard.rs"
    for i, line in enumerate(forge.read_text().splitlines(), 1):
        for cmd in re.findall(r'tag\("([\^~][A-Z0-9@]+)"', line):
            add("forge", cmd, "D", forge, i, crate="zpl-forge")
    go = ROOT / "_work/go-zpl/parse.go"
    source = go.read_text()
    start = source.index("func (p *parser) parseCaretCommand")
    end = source.index("func (p *parser) parseTildeCommand")
    block = source[start:end]
    for match in re.finditer(
        r"case ([\s\S]*?):([\s\S]*?)(?=\n\s*(?:case |default:)|\Z)", block
    ):
        ignored = any(
            '"' + c + '"' in match.group(1)
            for c in ["LR", "MN", "MF", "MC", "CV", "DN", "B3"]
        )
        line = source[: start + match.start()].count("\n") + 1
        for cmd in re.findall(r'"([A-Z][A-Z0-9])"', match.group(1)):
            add("go", "^" + cmd, "I" if ignored else "D", go, line, repo="go-zpl")
    evidence["ffi"] = dict(evidence["go"])
    binary = ROOT / "_work/BinaryKits.Zpl/src/BinaryKits.Zpl.Viewer/CommandAnalyzers"
    for path in sorted(binary.glob("*.cs")):
        for i, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            for cmd in re.findall(r'base\("([\^~][A-Z0-9@]+)"', line):
                add("binarykits", cmd, "D", path, i, repo="BinaryKits.Zpl")
    analyzer = ROOT / "_work/BinaryKits.Zpl/src/BinaryKits.Zpl.Viewer/ZplAnalyzer.cs"
    for cmd in ["^XA", "^XZ"]:
        add("binarykits", cmd, "D", analyzer, 1, repo="BinaryKits.Zpl")
    zplr = ROOT / "_work/zplr/docs/COMMAND_SUPPORT.md"
    for i, line in enumerate(zplr.read_text().splitlines(), 1):
        m = re.match(
            r"\| `([^`]+)` .*?\*\*(supported|partial|unsupported|non-rendering)\*\*",
            line,
        )
        if m:
            add(
                "zplr",
                m[1],
                {
                    "supported": "S",
                    "partial": "P",
                    "unsupported": "U",
                    "non-rendering": "N",
                }[m[2]],
                zplr,
                i,
                repo="zplr",
            )
    for crate, key in [("zpl-builder", "builder")]:
        literals(
            key,
            [packages[crate] / "src/builder.rs", packages[crate] / "src/elements.rs"],
            "E",
            crate=crate,
        )
    python = ROOT / "_work/python-zpl/zpl/label.py"
    literals("python", [python], "E", repo="python-zpl")
    for c in "23AQUCEX":
        add("python", "^B" + c, "E", python, 305, repo="python-zpl")
    literals(
        "jszpl",
        sorted((ROOT / "_work/jszpl/src/components").glob("*.ts")),
        "E",
        repo="jszpl",
    )
    # Dynamic font templates do not contain a literal font mnemonic.
    for key, path, kwargs in [
        (
            "builder",
            packages["zpl-builder"] / "src/elements.rs",
            {"crate": "zpl-builder"},
        ),
        ("python", python, {"repo": "python-zpl"}),
        ("jszpl", ROOT / "_work/jszpl/src/components/text.ts", {"repo": "jszpl"}),
    ]:
        add(key, "^A", "E", path, 1, **kwargs)
    # Generic raw-string APIs do not count as typed support for arbitrary commands.
    rows = []
    for cmd, page in index:
        cells = []
        for name in evidence:
            value = evidence[name].get(cmd)
            if value:
                cells.append(f"[{value['status']}]({value['source']})")
            elif name == "codyps-zpl":
                cells.append("F")
            else:
                cells.append("–")
        rows.append([f"`{cmd}`", page, ", ".join(params.get(cmd, [])) or "–", *cells])
    intro = """# ZPL command and argument comparison

[Browse by library or feature](../compatibility/README.md) · [Printer accuracy benchmark](accuracy/README.md) · [Performance comparison](README.md) · [Detailed argument limits](argument-support.md).

This is a **source-evidence inventory**, with a separate executed argument/accuracy matrix. Versions are the same pinned packages as the performance suite. The universe is the repository's 224-spelling [Zebra guide index](../zpl-command-index.tsv), including format/control aliases. `^A` represents the dynamic font-selection family; it does not mean every resident font is implemented. Non-Zebra extensions are excluded.

| Mark | Meaning |
| --- | --- |
| D | Explicit parser/render-path handler found. It may honor only some parameters; neither full rendering nor fidelity is implied. |
| I | Explicitly recognized but skipped or stored without the relevant raster effect. |
| F | codyps/zpl byte framer preserves command bytes only; no codyps/zpl renderer handler identified. Not semantic command support. |
| T | zpl-toolchain has a command specification/argument table. Requires the table-driven API and validation to use it; the performance suite's heuristic parse does not load it. No pixel renderer. |
| E | Typed builder emission path found. Generation is not parsing/rendering; emitted arguments may be fixed or incomplete. |
| S / P / U / N | ZPLr's own catalog says supported / partial / unsupported / non-rendering. These are **upstream claims**, independently tested only for the accuracy cases. |
| – | No explicit evidence found in the selected entry points. Not proof of absence: generic/dynamic handling and other modules may exist. |

Click a mark for the exact source or catalog location. Reference parameter keys are from zpl-toolchain's pinned specification, **not an assertion that each library implements those parameters**. The linked argument table records meaningful restrictions; the accuracy table executes concrete values. Firmware controls, networking, file operations and RFID are not pixel-rendering capabilities and are not sent to the printer by this suite.

The BinaryKits column inventories its Viewer, not the separate Label/Protocol emitters. Go and zpl-rs share one engine and the same parser evidence. Builders' raw escape hatches are deliberately not counted as universal typed support. A label that runs without errors can still silently lose a command or parameter.

## Explicit source evidence counts

Counts below are not interchangeable support percentages: a parser table, emitter, and rendering handler are different capabilities.

"""
    counts = []
    for n, values in evidence.items():
        inventory = [values[c]["status"] for c, _ in index if c in values]
        counts.append(
            [NAMES[n], *[inventory.count(k) for k in ["D", "I", "T", "E", "S", "P", "U", "N"]]]
        )
    output = (
        intro
        + table(["Adapter", "D", "I", "T", "E", "S", "P", "U", "N"], counts)
        + "\n## Complete command inventory\n\n"
        + table(["Command", "Guide page", "Reference parameters", *[NAMES[n] for n in evidence]], rows)
    )
    (REPO / "docs/benchmarks/command-support.md").write_text(output)
    (REPO / "docs/benchmarks/command-support.json").write_text(
        json.dumps(
            {
                "legend": "See command-support.md",
                "sources": locks,
                "commands": evidence,
                "parameter_keys": params,
                "descriptions": descriptions,
            },
            indent=2,
        )
        + "\n"
    )
    print("Generated", len(index), "command rows")


if __name__ == "__main__":
    main()
