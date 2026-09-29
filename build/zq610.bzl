"""Native ZQ610 evidence matrix, independently cached per renderer and case."""

def zq610_matrix(ctx, files, compiled, catalog, libraries, invoke, stage):
    root = "references/zq610-candidates/"
    manifest = catalog[root + "manifest.json"]
    saved = {(r["case"], r["library"]): r for r in catalog[root + "saved/results.json"]["results"]}
    service = {r["name"]: r for r in manifest.get("labelary", [])}
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
            spec = {"source": files[case["source"]].path, "sha256": case["sha256"],
                    "width": case["width"], "height": case["height"], "row": identity, "timeout": 30}
            if lib == "codyps-zpl":
                spec["render_profile"] = "zq610-plus-203dpi"
            inputs = [files[case["source"]]]
            if ctx.attr.saved:
                evidence = saved.get((name, lib))
                if evidence == None:
                    fail("Missing saved ZQ610 candidate result: %s/%s; build suite_zq610_candidates and save results first" % (name, lib))
                if lib == "codyps-zpl" and evidence.get("profile") != identity["profile"]:
                    fail("Stale saved ZQ610 profile: " + name + "; rerender and save candidates")
                if evidence["source_sha256"] != case["sha256"] or evidence["reference_sha256"] != case["png_sha256"]:
                    fail("Stale saved ZQ610 candidate evidence: %s/%s" % (name, lib))
                png = files[root + "saved/images/" + name + "-" + lib + ".png"] if evidence["status"] in ["rendered", "blank"] else None
                spec = {"row": evidence, "image": png.path if png else None}
                inputs = [png] if png else []
            elif lib == "labelary":
                capture = service.get(name)
                spec["saved"] = ""
                spec["row"] = dict(identity, status = "not_captured", diagnostic = "No authorized saved Labelary observation for this input")
                if capture:
                    if capture["sha256"] != case["sha256"] or [capture["width"], capture["height"]] != [case["width"], case["height"]]:
                        fail("Stale Labelary source or dimensions: " + name)
                    spec["row"] = dict(identity, status = capture["status"], diagnostic = capture.get("diagnostic", ""), observed_utc = capture["received_utc"])
                    if capture["status"] == "rendered":
                        png = files[root + "labelary/" + capture["image"]]
                        spec.update(saved = png.path, png_sha256 = capture["png_sha256"])
                        inputs.append(png)
            else:
                spec["library"] = compiled[lib].path
                inputs.append(compiled[lib])
            invoke(ctx, "saved" if ctx.attr.saved else "render", key, spec, inputs, [row, raster])
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
              (files[root + "saved/results.json"], "_candidate_saved.json"),
              (files["benchmarks/sources.lock.json"], "benchmarks/sources.lock.json")] + rows + publish
    inputs += [(files[c[k]], c[k]) for c in manifest["cases"] for k in ["source", "reference"]]
    inputs += [(f, "_candidate_libraries/" + lib) for lib, f in compiled.items()]
    pages = stage(ctx, "zq610-candidate-pages", inputs, [["benchmarks/zq610_candidate_pages.py"]])
    return [(pages, "")] + publish
