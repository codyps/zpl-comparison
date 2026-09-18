#!/usr/bin/env python3
"""Markdown, static plots, and argument matrix from saved accuracy measurements."""

import json
import os
from pathlib import Path
import sys
import statistics

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "_work/matplotlib"))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(ROOT))
from report import NAMES, table  # noqa: E402
from accuracy.gallery import generate  # noqa: E402

LIBRARIES = ["local", "labelize", "forge", "go", "ffi", "binarykits", "zplr"]


def main():
    dest = Path(sys.argv[1])
    data = json.loads((dest / "results.json").read_text())
    generate(dest)
    rows = data["results"]
    cases = data["cases"]
    scored = [r for r in rows if r["score"] is not None]
    valid = {r["case"] for r in scored}
    common = {
        c
        for c in valid
        if all(r["status"] == "rendered" for r in rows if r["case"] == c)
    }
    groups = sorted({c["group"] for c in cases})
    summary = []
    for name in LIBRARIES:
        samples = [r for r in scored if r["library"] == name]
        shared = [r["score"] for r in samples if r["case"] in common]
        summary.append(
            [
                NAMES[name],
                sum(r["status"] == "rendered" for r in samples),
                sum(r.get("ink_exact", False) for r in samples),
                sum(r.get("exact", False) for r in samples),
                sum(r["status"] == "error" for r in samples),
                sum(r["status"] == "blank" for r in samples),
                f"{statistics.mean(r['score'] for r in samples) * 100:.2f}%",
                f"{statistics.mean(r['score'] for r in samples if r['group'] != 'barcode-formats') * 100:.2f}%",
                f"{statistics.mean(r['score'] for r in samples if r['group'] == 'barcode-formats') * 100:.2f}%",
                f"{statistics.mean(shared) * 100:.2f}%" if shared else "N/A",
            ]
        )
    plot = (
        np.array(
            [
                [
                    statistics.mean(
                        r["score"]
                        for r in scored
                        if r["library"] == n and r["group"] == g
                    )
                    for g in groups
                ]
                for n in LIBRARIES
            ]
        )
        * 100
    )
    fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
    image = ax.imshow(plot, vmin=0, vmax=100, cmap="viridis", aspect="auto")
    ax.set_xticks(range(len(groups)), groups, rotation=25, ha="right")
    ax.set_yticks(range(len(LIBRARIES)), [NAMES[n] for n in LIBRARIES])
    for y in range(len(LIBRARIES)):
        for x in range(len(groups)):
            ax.text(
                x,
                y,
                f"{plot[y, x]:.1f}",
                ha="center",
                va="center",
                color="white" if plot[y, x] < 55 else "black",
            )
    ax.set_title("Mean foreground IoU (%) – failed/blank renders count as zero")
    fig.colorbar(image, ax=ax, label="%")
    fig.savefig(dest / "accuracy.svg", metadata={"Date": None})
    fig.savefig(dest / "accuracy.png", dpi=120)
    plt.close(fig)
    ref = data["fresh_reference"]
    text = [
        "# Accuracy against a real Zebra printer\n",
        "**[Compare images by library or case](comparisons/README.md)**: printer preview, library render and difference together.\n",
        f"Reference: **{ref['device']}, firmware {ref['firmware']}**, {ref['dpi']} dpi. Fresh captures: {ref['captured_utc']}. Library comparisons: {data['measured_utc']}.\n",
        "[Command/argument support](../command-support.md) · [Run/reproduce](../../../benchmarks/accuracy/README.md) · [Raw measurements](results.json).\n",
        "**This measures fidelity to the printer’s HTTP preview raster, not physical printed/scanned labels.** "
        "Every renderer receives the exact same captured ZPL. No scaling, alignment search, cropping, or replacement by another renderer’s output. "
        "Different canvas sizes are placed at the same origin on a white union canvas, with the size mismatch reported separately.\n",
        f"{len(cases)} cases, {len(valid)} with nonblank printer references, {len(LIBRARIES)} renderer adapters. "
        "The repeated first/last capture matched exactly. Parser-only zpl-toolchain and the three builders (Rust zpl-builder, Python ZPL, JSZPL) cannot render incoming ZPL: **N/A**, not an accuracy score of zero.\n",
        "## How to read the score\n",
        "**Foreground IoU = matching black pixels / pixels black in either image.** "
        "It avoids making an empty label look accurate because most pixels are white. The fixed threshold is gray <128 after compositing transparency onto white. "
        "Missing and extra pixels, precision, recall and full-canvas mismatch are retained per cell in JSON. "
        "Errors and blank library output score zero for a nonblank printer reference; blank printer references are quarantined from scores. "
        "“Ink exact” permits only all-white canvas margins to differ; “strict exact” additionally requires identical dimensions.\n",
        f"The all-case mean weights each nonblank case equally, including unsupported cases. Shared-case mean uses the **{len(common)} cases** for which all seven adapters returned nonblank rasters; it isolates a smaller common subset and is subject to selection bias. The corpus is broad but not representative of every deployment.\n",
        "![Mean foreground IoU](accuracy.svg)\n",
        table(
            [
                "Library",
                f"Nonblank / {len(valid)}",
                "Ink exact",
                "Strict exact",
                "Errors",
                "Blank",
                "All-case mean IoU",
                "Fresh argument IoU",
                "Archived barcode IoU",
                "Shared-case mean IoU",
            ],
            summary,
        ),
        "The model-2 QR probe illustrates a placement error: the printer starts the symbol near y=119, while codyps/zpl starts it at y=60. IoU retains that difference rather than aligning it away. Inspect the images to distinguish placement, font metrics, omitted fields and symbol-pattern differences.\n",
        "\n## Limits and provenance\n",
        "The 60 archived barcode cases were used during development of this repository, so they are **not an independent holdout**. "
        "Fresh probes cover multiple font sizes (including codyps/zpl’s native 32-dot strike), other resident fonts, rotations, positioning, block alignment/indentation, colors, graphic encodings and barcode arguments. "
        "Argument combinations, payloads and sizes are finite samples, not proofs of full support. Different valid barcode encodings/masks may scan identically yet differ in pixels; this score measures visual agreement, not barcode validity. "
        "Captured fonts and preview behavior are specific to this device/firmware. No persistent device configuration, flash/font downloads, RFID operations or physical print jobs are exercised.\n",
        "ZPLr and BinaryKits may use host font fallback; installed font availability can affect other hosts. The Go and Rust-FFI rows share the same renderer, so they are not independent implementations. "
        "A successful process or a recognized command is not evidence that its arguments were honored. Inspect the exact inputs and difference images.\n",
        "## Per-case accuracy and argument comparison\n",
        "Click any result to compare the printer preview, library render and difference together, or inspect a render error. "
        "Difference colors: black=agreement, magenta=printer only, cyan=library only. Input links show the exact argument values.\n",
    ]
    for group in groups:
        text.append(f"### {group}\n")
        tab = []
        for case in cases:
            if case["group"] != group:
                continue
            label = f"[{case['name']}](../../../{case['zpl']}) · [printer](../../../{case['reference']})"
            values = []
            for n in LIBRARIES:
                r = next(
                    r for r in rows if r["case"] == case["id"] and r["library"] == n
                )
                if r["score"] is None:
                    label_text = "reference blank"
                elif r["status"] != "rendered":
                    label_text = r["status"]
                else:
                    label_text = f"{r['score'] * 100:.1f}%"
                values.append(f"[{label_text}](comparisons/cases/{case['id']}.md#{n})")
            tab.append(
                [label, case["command"], case["arguments"].replace("|", "/"), *values]
            )
        text.append(table(["Case", "Command", "Argument values", *LIBRARIES], tab))
    text.append(
        "\nErrors and diagnostics are retained in [results.json](results.json); no failed case is dropped from its eligible denominator.\n"
    )
    (dest / "README.md").write_text("\n".join(text))


if __name__ == "__main__":
    main()
