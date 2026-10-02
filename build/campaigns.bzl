"""Remeasure local public-label and paired-printer campaigns in CI."""

def campaigns(ctx, files, compiled, baseline, catalog, observe, invoke, stage, select):
    public_rows = []
    public_images = []
    paired_rows = []
    paired_images = []
    definitions = []
    for case in catalog["test-data/public-zpl/manifest.json"]["cases"]:
        definitions.append(("public", case["name"], "test-data/public-zpl/" + case["file"], case["sha256"],
                            case["width"], case["height"], "zd621-203dpi",
                            "references/public-zd621-20261002/" + case["name"] + ".png",
                            "docs/public-examples/images/" + case["name"] + ".png"))
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
                                root + ".png", root + "-local.png"))
    public_refs = {r["name"]: r["png_sha256"] for r in catalog["references/public-zd621-20261002/manifest.json"]["cases"]}
    for suite, name, source, digest, width, height, profile, reference, image_dest in definitions:
        key = suite + "/" + name + "-codyps-zpl"
        row = ctx.actions.declare_file(ctx.label.name + "_actions/" + key + ".render.json")
        raster = ctx.actions.declare_directory(ctx.label.name + "_actions/" + key + ".render")
        spec = {"source_name": source, "source": files[source].path, "sha256": digest,
                "width": width, "height": height, "render_profile": profile, "timeout": 30,
                "row": {"case": name, "library": "codyps-zpl", "group": suite}}
        observe(ctx, key, "codyps-zpl", spec, files, compiled, baseline, {}, row, raster)
        scored = ctx.actions.declare_file(ctx.label.name + "_actions/" + key + ".comparison.json")
        diff = ctx.actions.declare_directory(ctx.label.name + "_actions/" + key + ".diff")
        reference_hash = public_refs[name] if suite == "public" else paired["files"][reference[len("references/zq610-plus-v1/"): ]]
        invoke(ctx, "compare", key + "-compare", {"suite": suite, "row": row.path, "image": raster.path,
               "reference": files[reference].path, "sha256": reference_hash, "strict_native_canvas": True},
               [row, raster, files[reference]], [scored, diff])
        if suite == "public":
            public_rows.append((scored, "_public_rows/" + name + ".json"))
            public_images += [(raster, image_dest), (diff, image_dest[:-4] + "-diff.png")]
        else:
            paired_rows.append((scored, "_paired_rows/" + name + ".json"))
            paired_images.append((raster, image_dest))
    shared = select(files, ["benchmarks/accuracy/", "benchmarks/conformance.py", "benchmarks/formatting.py", "benchmarks/report.py", "benchmarks/sources.lock.json"])
    public_inputs = shared + select(files, ["build/public_report.py", "benchmarks/public_examples.py", "benchmarks/labelary.py", "test-data/", "docs/zpl-command-index.tsv", "references/", "docs/benchmarks/labelary/"])
    public = stage(ctx, "public-report", public_inputs + public_rows + public_images, [["build/public_report.py"]])
    paired_inputs = shared + select(files, ["build/paired_report.py", "benchmarks/zq610_pages.py", "references/zq610-plus-v1/"])
    paired_report = stage(ctx, "paired-report", paired_inputs + paired_rows + paired_images, [["build/paired_report.py"]])
    return public, paired_report, public_images + paired_images
