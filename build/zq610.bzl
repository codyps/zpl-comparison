"""Native ZQ610 evidence matrix, independently cached per renderer and case."""

def zq610_matrix(ctx, files, compiled, baseline, catalog, libraries, observe, invoke, stage):
    root = "references/zq610-candidates/"
    manifest = catalog[root + "manifest.json"]
    service = {(r["sha256"], r["width"], r["height"]): dict(r, image_root = root + "labelary/") for r in manifest.get("labelary", [])}
    publish = []
    rows = []
    for case in manifest["cases"]:
        name = case["name"]
        for lib in libraries:
            key = "zq610-candidates/" + name + "-" + lib
            row = ctx.actions.declare_file(ctx.label.name + "_actions/" + key + ".render.json")
            raster = ctx.actions.declare_directory(ctx.label.name + "_actions/" + key + ".render")
            identity = {"case": name, "library": lib, "group": "zq610", "score": None,
                        "source_sha256": case["sha256"], "reference_sha256": case["png_sha256"],
                        "requested_dimensions": [case["width"], case["height"]],
                        "profile": "ZQ610_PLUS_203_DPI; exact source and native requested canvas" if lib == "codyps-zpl" else "pinned library defaults; exact source and native requested canvas"}
            spec = {"source": files[case["source"]].path, "source_name": case["source"], "sha256": case["sha256"],
                    "width": case["width"], "height": case["height"], "row": identity, "timeout": 30}
            if lib == "codyps-zpl":
                spec["render_profile"] = "zq610-plus-203dpi"
            observe(ctx, key, lib, spec, files, compiled, baseline, service, row, raster)
            scored = ctx.actions.declare_file(ctx.label.name + "_actions/" + key + ".comparison.json")
            diff = ctx.actions.declare_directory(ctx.label.name + "_actions/" + key + ".diff")
            reference = files[case["reference"]]
            invoke(ctx, "compare", key + "-compare", {"suite": "zq610", "row": row.path, "image": raster.path,
                   "reference": reference.path, "sha256": case["png_sha256"], "strict_native_canvas": True},
                   [row, raster, reference], [scored, diff])
            rows.append((scored, "_candidate_rows/" + name + "-" + lib + ".json"))
            publish.extend([(raster, "docs/benchmarks/zq610-candidates/images/" + name + "-" + lib + ".png"),
                            (diff, "docs/benchmarks/zq610-candidates/images/" + name + "-" + lib + "-diff.png")])
    inputs = [(files["benchmarks/zq610_candidate_pages.py"], "benchmarks/zq610_candidate_pages.py"),
              (files[root + "manifest.json"], root + "manifest.json"),
              (files["benchmarks/sources.lock.json"], "benchmarks/sources.lock.json")] + rows + publish
    inputs += [(files[c[k]], c[k]) for c in manifest["cases"] for k in ["source", "reference"]]
    inputs += [(f, "_candidate_libraries/" + lib) for lib, f in compiled.items()]
    pages = stage(ctx, "zq610-candidate-pages", inputs, [["benchmarks/zq610_candidate_pages.py"]])
    return [(pages, "")] + publish
