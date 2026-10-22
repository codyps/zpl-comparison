"""300-DPI GX430t native preview campaign, cached per case and renderer."""

def gx430t_matrix(ctx, files, compiled, baseline, catalog, libraries, observe, invoke, stage, select):
    root = "references/gx430t-300-v1/"
    base = "docs/benchmarks/gx430t-300dpi"
    manifest = catalog[root + "manifest.json"]
    service_manifest = catalog[root + "labelary/captures.json"]
    if service_manifest["status"] != "complete" or service_manifest["dpmm"] != 12 or service_manifest["dpi"] != 300:
        fail("GX430t requires complete 12-dpmm Labelary captures")
    service = {}
    for capture in service_manifest["cases"]:
        if capture.get("dpmm") != 12 or capture.get("dpi") != 300:
            fail("GX430t Labelary observation has the wrong density")
        service[(capture["sha256"], capture["width"], capture["height"])] = dict(capture, image_root = root + "labelary/")
    rows = []
    images = []
    for case in manifest["cases"]:
        name = case["name"]
        for lib in libraries:
            key = "gx430t-300dpi/" + name + "-" + lib
            row = ctx.actions.declare_file(ctx.label.name + "_actions/" + key + ".render.json")
            raster = ctx.actions.declare_directory(ctx.label.name + "_actions/" + key + ".render")
            spec = {"source_name": case["source"], "source": files[case["source"]].path,
                    "sha256": case["sha256"], "width": case["width"], "height": case["height"],
                    "timeout": 30, "render_profile": "gx430t-300dpi",
                    "row": {"case": name, "library": lib, "group": case["group"], "dpi": 300}}
            if lib == "labelary":
                spec["row"]["service_capture"] = service[(case["sha256"], case["width"], case["height"])]
            observe(ctx, key, lib, spec, files, compiled, baseline, service, row, raster)
            scored = ctx.actions.declare_file(ctx.label.name + "_actions/" + key + ".comparison.json")
            diff = ctx.actions.declare_directory(ctx.label.name + "_actions/" + key + ".diff")
            reference = files[case["reference"]]
            invoke(ctx, "compare", key + "-compare", {"suite": "gx430t-300dpi", "row": row.path,
                   "image": raster.path, "reference": reference.path,
                   "sha256": case["reference_sha256"], "strict_native_canvas": True},
                   [row, raster, reference], [scored, diff])
            rows.append((scored, "_gx430t_rows/" + name + "-" + lib + ".json"))
            images.extend([(raster, base + "/images/" + name + "-" + lib + ".png"),
                           (diff, base + "/images/" + name + "-" + lib + "-diff.png")])
    inputs = select(files, ["benchmarks/gx430t.py", "benchmarks/gx430t_labelary.py", "benchmarks/labelary.py", "benchmarks/campaigns.py", "benchmarks/accuracy/",
                           "benchmarks/conformance.py", "benchmarks/formatting.py", "benchmarks/report.py",
                           "benchmarks/sources.lock.json", root])
    report = stage(ctx, "gx430t-report", inputs + rows + images,
                   [["benchmarks/gx430t.py", "--report"] + libraries])
    return [(report, "")] + images
