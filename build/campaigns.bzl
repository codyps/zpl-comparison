"""Remeasure local public-label and paired-printer campaigns in CI."""

def campaigns(ctx, files, compiled, baseline, catalog, libraries, observe, invoke, stage, select):
    public_rows = []
    public_images = []
    paired_rows = []
    paired_images = []
    definitions = []
    for case in catalog["test-data/public-zpl/manifest.json"]["cases"]:
        definitions.append(("public", case["name"], "test-data/public-zpl/" + case["file"], case["sha256"],
                            case["width"], case["height"], "zd621-203dpi",
                            "references/public-zd621-20261002/" + case["name"] + ".png"))
    paired = catalog["references/zq610-plus-v1/manifest.json"]
    for name, case in paired["cases"].items():
        if any([case["status"].get(p, {}).get("status") != "captured" for p in ["zq610", "zd621"]]):
            continue
        for printer in ["zq610", "zd621"]:
            status = case["status"][printer]
            width, height = status["measurement"]["dimensions"]
            root = "references/zq610-plus-v1/" + name + "/" + printer
            definitions.append(("paired", name + "-" + printer, root + ".zpl", status["submitted_sha256"],
                                width, height, "zq610-plus-203dpi" if printer == "zq610" else "zd621-preview-203dpi",
                                root + ".png"))
    public_refs = {r["name"]: r["png_sha256"] for r in catalog["references/public-zd621-20261002/manifest.json"]["cases"]}
    captures = {}
    for root, rows in [
        ("docs/benchmarks/labelary/", catalog["docs/benchmarks/labelary/captures.json"]["cases"]),
        ("references/zq610-candidates/labelary/", catalog["references/zq610-candidates/manifest.json"]["labelary"]),
        ("references/paired-labelary/", catalog["references/paired-labelary/captures.json"]["cases"]),
    ]:
        for capture in rows:
            captures[(capture["sha256"], capture["width"], capture["height"])] = dict(capture, image_root = root)
    for suite, name, source, digest, width, height, profile, reference in definitions:
        for lib in libraries:
            key = suite + "/" + name + "-" + lib
            row = ctx.actions.declare_file(ctx.label.name + "_actions/" + key + ".render.json")
            raster = ctx.actions.declare_directory(ctx.label.name + "_actions/" + key + ".render")
            spec = {"source_name": source, "source": files[source].path, "sha256": digest,
                    "width": width, "height": height, "timeout": 30,
                    "row": {"case": name, "library": lib, "group": suite}}
            if lib in ["codyps-zpl", "codyps-zpl-node"]:
                spec["render_profile"] = profile
            if lib == "labelary" and (digest, width, height) in captures:
                spec["row"]["service_capture"] = captures[(digest, width, height)]
            observe(ctx, key, lib, spec, files, compiled, baseline, captures, row, raster)
            scored = ctx.actions.declare_file(ctx.label.name + "_actions/" + key + ".comparison.json")
            diff = ctx.actions.declare_directory(ctx.label.name + "_actions/" + key + ".diff")
            reference_hash = public_refs[name] if suite == "public" else paired["files"][reference[len("references/zq610-plus-v1/"): ]]
            invoke(ctx, "compare", key + "-compare", {"suite": suite, "row": row.path, "image": raster.path,
                   "reference": files[reference].path, "sha256": reference_hash, "strict_native_canvas": True},
                   [row, raster, files[reference]], [scored, diff])
            base = "docs/public-examples" if suite == "public" else "docs/benchmarks/zq610-plus"
            image_dest = base + "/images/" + name + "-" + lib + ".png"
            rows = public_rows if suite == "public" else paired_rows
            images = public_images if suite == "public" else paired_images
            rows.append((scored, "_" + suite + "_rows/" + name + "-" + lib + ".json"))
            images.extend([(raster, image_dest), (diff, image_dest[:-4] + "-diff.png")])
    shared = select(files, ["benchmarks/campaigns.py", "benchmarks/accuracy/", "benchmarks/conformance.py", "benchmarks/formatting.py", "benchmarks/report.py", "benchmarks/sources.lock.json"])
    public_inputs = shared + select(files, ["build/public_report.py", "benchmarks/public_examples.py", "benchmarks/labelary.py", "test-data/", "docs/zpl-command-index.tsv", "references/", "docs/benchmarks/labelary/"])
    public = stage(ctx, "public-report", public_inputs + public_rows + public_images, [["build/public_report.py"] + libraries])
    paired_inputs = shared + select(files, ["build/paired_report.py", "benchmarks/zq610_pages.py", "references/zq610-plus-v1/"])
    paired_report = stage(ctx, "paired-report", paired_inputs + paired_rows + paired_images, [["build/paired_report.py"] + libraries])
    return public, paired_report, public_images + paired_images
