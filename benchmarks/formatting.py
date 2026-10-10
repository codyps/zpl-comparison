"""Shared library names and Markdown tables, with no plotting dependencies."""

NAMES = {
    "codyps-zpl-go": "codyps/zpl (Go / wasm2go)",
    "codyps-zpl-node": "codyps/zpl (Node / WASM)",
    "labelary": "Labelary (SaaS)",
    "codyps-zpl": "codyps/zpl (Rust)",
    "toolchain": "zpl-toolchain (Rust)",
    "forge": "zpl-forge (Rust)",
    "labelize": "labelize (Rust)",
    "ffi": "zpl-rs (Rust → Go)",
    "go": "go-zpl (Go)",
    "binarykits": "BinaryKits.Zpl (.NET)",
    "zplr": "ZPLr (TypeScript)",
    "zebrash": "Zebrash (Go)",
    "zpl-renderer-js": "zpl-renderer-js (WASM)",
    "zebrash-ts": "zebrash-ts (TypeScript)",
    "builder": "zpl-builder (Rust)",
    "python": "Python ZPL",
    "jszpl": "JSZPL (TypeScript)",
}


def table(headers, rows):
    return (
        "\n".join(
            [
                "| " + " | ".join(headers) + " |",
                "| " + " | ".join(["---"] * len(headers)) + " |",
            ]
            + ["| " + " | ".join(map(str, r)) + " |" for r in rows]
        )
        + "\n"
    )
