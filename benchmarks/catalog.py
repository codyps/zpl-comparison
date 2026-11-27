#!/usr/bin/env python3
"""Compose the maintained capabilities survey with collected popularity and pins."""

import json
import argparse
from pathlib import Path
import re
import tomllib

from formatting import table

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent


def package_versions():
    rust = tomllib.loads((ROOT / "adapters/rust/Cargo.lock").read_text())["package"]
    selected = {"zpl_toolchain_core", "labelize", "zpl-forge", "zpl-rs", "zpl-builder"}
    versions = {p["name"]: p["version"] for p in rust if p["name"] in selected}
    node = json.loads((ROOT / "adapters/node/package-lock.json").read_text())[
        "packages"
    ]
    versions.update(
        {name: node["node_modules/" + name]["version"] for name in ["jszpl", "zplr"]}
    )
    for adapter, package in [("zpl-renderer-js", "zpl-renderer-js"), ("zebrash-ts", "@zebrash/node"), ("zplkit-ts", "@zplkit/render")]:
        lock = json.loads((ROOT / "adapters" / adapter / "package-lock.json").read_text())
        versions[adapter] = lock["packages"]["node_modules/" + package]["version"]
    sources = json.loads((ROOT / "sources.lock.json").read_text())
    versions["zebrash"] = sources["zebrash"]["version"]
    versions["zplkit"] = sources["zplkit"]["version"]
    dotnet = json.loads((ROOT / "adapters/dotnet/packages.lock.json").read_text())[
        "dependencies"
    ]["net10.0"]
    versions.update(
        {
            "binarykits-viewer": dotnet["BinaryKits.Zpl.Viewer"]["resolved"],
            "binarykits-label": dotnet["BinaryKits.Zpl.Label"]["resolved"],
        }
    )
    neodynamic = json.loads((ROOT / "adapters/neodynamic/packages.lock.json").read_text())["dependencies"]["net10.0"]
    versions["neodynamic"] = neodynamic["Neodynamic.SDK.ZPLPrinter"]["resolved"]
    return versions


def library_identities(locks, versions):
    """Pinned version label and upstream page for every compared library key."""
    def tree(key, sub=""):
        return f"{locks[key]['url']}/tree/{locks[key]['rev']}" + (f"/{sub}" if sub else "")

    def short(key):
        return locks[key]["rev"][:7]

    def npm(package, version):
        return f"https://www.npmjs.com/package/{package}/v/{version}"

    def nuget(package, version):
        return f"https://www.nuget.org/packages/{package}/{version}"

    v = versions
    entries = {
        "codyps-zpl": (f"{locks['zpl']['version']} ({short('zpl')})", tree("zpl")),
        "codyps-zpl-go": (short("zpl"), tree("zpl", "zpl-go")),
        "codyps-zpl-node": (short("zpl"), tree("zpl", "zpl-node")),
        "toolchain": (v["zpl_toolchain_core"], f"https://docs.rs/zpl_toolchain_core/{v['zpl_toolchain_core']}"),
        "labelize": (v["labelize"], f"https://docs.rs/labelize/{v['labelize']}"),
        "forge": (v["zpl-forge"], f"https://docs.rs/zpl-forge/{v['zpl-forge']}"),
        "ffi": (v["zpl-rs"], f"https://docs.rs/crate/zpl-rs/{v['zpl-rs']}"),
        "builder": (v["zpl-builder"], f"https://docs.rs/zpl-builder/{v['zpl-builder']}"),
        "go": (short("go-zpl"), tree("go-zpl")),
        "zebrash": (v["zebrash"], tree("zebrash")),
        "binarykits": (v["binarykits-viewer"], nuget("BinaryKits.Zpl.Viewer", v["binarykits-viewer"])),
        "neodynamic": (v["neodynamic"], nuget("Neodynamic.SDK.ZPLPrinter", v["neodynamic"])),
        "zplr": (v["zplr"], npm("zplr", v["zplr"])),
        "jszpl": (v["jszpl"], npm("jszpl", v["jszpl"])),
        "zpl-renderer-js": (v["zpl-renderer-js"], npm("zpl-renderer-js", v["zpl-renderer-js"])),
        "zebrash-ts": (v["zebrash-ts"], npm("@zebrash/node", v["zebrash-ts"])),
        "zplkit-ts": (v["zplkit-ts"], npm("@zplkit/render", v["zplkit-ts"])),
        "zplkit": (v["zplkit"], tree("zplkit")),
        "python": (short("python-zpl"), tree("python-zpl")),
        # The service exposes no renderer version; captures record dates instead.
        "labelary": (None, "https://labelary.com/service.html"),
    }
    return {lib: {"version": version, "url": url} for lib, (version, url) in entries.items()}


def render(template, popularity, locks, versions=None):
    observed = popularity.get("observed_utc", "historical snapshot; observation time not recorded")
    popularity = popularity.get("repositories", popularity)
    def replace(match):
        token = match.group(1)
        if token == "zpl_revision":
            return locks["zpl"]["rev"]
        if token == "popularity_table":
            return ("Observed: " + str(observed or "unavailable") + ".\n\n" + table(
                ["Repository", "Stars", "Forks", "Last push in saved snapshot (UTC)"],
                [
                    [
                        f"[{repo}](https://github.com/{repo})",
                        row["stargazers_count"],
                        row["forks_count"],
                        row["pushed_at"],
                    ]
                    for repo, row in sorted(
                        popularity.items(),
                        key=lambda item: (-item[1]["stargazers_count"], item[0]),
                    )
                ],
            ).rstrip())
        kind, repo = token.split(":", 1)
        if kind == "rev":
            return locks[repo]["rev"]
        if kind == "version":
            return versions[repo]
        field = {"stars": "stargazers_count", "forks": "forks_count"}[kind]
        return str(popularity.get(repo, {}).get(field, "unavailable"))

    return (
        "<!-- Generated by benchmarks/catalog.py from benchmarks/templates/capabilities.md and saved data. -->\n\n"
        + re.sub(r"\{\{([^{}]+)\}\}", replace, template)
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--popularity", type=Path, default=ROOT / "popularity.json")
    parser.add_argument("--output", type=Path, default=REPO / "docs/benchmarks/capabilities.md")
    args = parser.parse_args(argv)
    popularity = json.loads(args.popularity.read_text()) if args.popularity.exists() else dict(observed_utc=None, repositories={})
    if not args.popularity.exists():
        args.popularity.write_text(json.dumps(popularity, indent=2) + "\n")
    locks = json.loads((ROOT / "sources.lock.json").read_text())
    versions = package_versions()
    result = render(
        (ROOT / "templates/capabilities.md").read_text(),
        popularity,
        locks,
        versions,
    )
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result)
    (output.parent / "libraries.json").write_text(
        json.dumps(library_identities(locks, versions), indent=2, sort_keys=True) + "\n"
    )
    print("Generated capabilities survey and popularity table")


if __name__ == "__main__":
    main()
