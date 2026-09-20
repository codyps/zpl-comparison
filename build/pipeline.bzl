"""Fine-grained report action graph; no rendering in report assembly."""

load("@report_catalog//:catalog.bzl", "CATALOG")

LIBRARIES = ["codyps-zpl", "labelize", "forge", "go", "ffi", "binarykits", "zplr", "labelary"]

def _invoke(ctx, kind, name, spec, inputs, outputs):
    manifest = ctx.actions.declare_file(ctx.label.name + "_actions/" + name + ".json")
    ctx.actions.write(manifest, json.encode(spec))
    runner = getattr(ctx.attr, "_" + kind)
    worker = kind != "stage"
    parameters = ctx.actions.declare_file(ctx.label.name + "_actions/" + name + ".params")
    ctx.actions.write(parameters, "\n".join([manifest.path] + [f.path for f in outputs]))
    ctx.actions.run(
        executable = runner[DefaultInfo].files_to_run.executable,
        arguments = [kind, "@" + parameters.path] if worker else [manifest.path] + [f.path for f in outputs],
        inputs = depset(inputs + [manifest, parameters]),
        tools = [runner[DefaultInfo].files_to_run],
        outputs = outputs,
        execution_requirements = {"supports-workers": "1", "requires-worker-protocol": "json"} if worker else {},
        mnemonic = "Zpl" + kind.capitalize(),
        progress_message = "%s %s" % (kind, name),
        env = {"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1", "MPLBACKEND": "Agg"},
    )

def _file(ctx, name):
    return ctx.actions.declare_file(ctx.label.name + "_actions/" + name)

def _tree(ctx, name):
    return ctx.actions.declare_directory(ctx.label.name + "_actions/" + name)

def _stage(ctx, name, inputs, commands, assemble = False):
    output = ctx.actions.declare_directory(ctx.label.name) if assemble else _tree(ctx, name)
    _invoke(ctx, "stage", name, {"inputs": [[f.path, dest] for f, dest in inputs], "commands": commands, "assemble": assemble}, [f for f, _ in inputs], [output])
    return output

def _select(files, prefixes):
    return [(f, p) for p, f in files.items() if any([p.startswith(prefix) for prefix in prefixes])]

def _impl(ctx):
    files = {f.short_path: f for f in ctx.files.srcs}
    compiled = {name: target[DefaultInfo].files.to_list()[0] for name, target in zip(LIBRARIES[:-1], ctx.attr.libraries)}
    captures = {(r["sha256"], r["width"], r["height"]): r for r in CATALOG["docs/benchmarks/labelary/captures.json"]["cases"]}
    publish = []
    aggregates = []
    groups = {}

    # Maintained documents, captured evidence, and scripts remain downloadable.
    static = [(f, p) for p, f in files.items() if not (p.startswith("docs/benchmarks/") and (("/images/" in p and not p.startswith("docs/benchmarks/labelary/")) or p in ["docs/benchmarks/" + s + "/results.json" for s in ["accuracy", "conformance", "external-zpl"]]))]
    for suite in ["accuracy", "conformance", "external-zpl"]:
        saved = CATALOG["docs/benchmarks/" + suite + "/results.json"]
        renders = "docs/benchmarks/" + suite
        base = "docs/benchmarks/accuracy/comparisons" + ("" if suite == "accuracy" else "/features" if suite == "conformance" else "/external")
        assets = renders if suite == "accuracy" else base
        corpus = "test-data/render-conformance" if suite == "conformance" else "test-data/external-zpl"
        cases = saved["cases"] if suite == "accuracy" else CATALOG[corpus + "/manifest.json"]["cases"]
        reference_dir = "benchmarks/accuracy/" + ("conformance-reference" if suite == "conformance" else "external-reference")
        references = {} if suite == "accuracy" else {r["name"]: r for r in CATALOG[reference_dir + "/manifest.json"]["cases"]}
        failures = {} if suite == "accuracy" else {r["name"]: r for r in CATALOG[reference_dir + "/manifest.json"].get("failures", [])}
        if suite == "accuracy":
            fresh = CATALOG["benchmarks/accuracy/reference/manifest.json"]
            archive = CATALOG["references/barcodes-zd621-v1/manifest.json"]
            old_cases = {c["id"]: c for c in saved["cases"]}
            cases = [dict(c, id = "argument-" + c["name"], source = "fresh arguments", zpl = "benchmarks/accuracy/reference/" + c["name"] + ".zpl", reference = "benchmarks/accuracy/reference/" + c["name"] + ".png") for c in fresh["cases"] if c["group"] != "repeatability"]
            for name, c in archive["cases"].items():
                cases.append(dict(id = "barcode-" + name, name = name, group = "barcode-formats", command = old_cases.get("barcode-" + name, {}).get("command", "See ZPL"), arguments = "See exact archived ZPL", width = archive["width"], height = 1218, source = "archived barcode development corpus", zpl = "references/barcodes-zd621-v1/" + name + ".zpl", reference = "references/barcodes-zd621-v1/" + name + ".png", zpl_sha256 = c["zpl_sha256"], png_sha256 = c["printer_png_sha256"]))
        compared = []
        rendered = []
        relation_groups = {}
        for case in cases:
            cid = case.get("id", case["name"])
            zpl = case["zpl"] if suite == "accuracy" else corpus + "/" + case["file"]
            digest = case["zpl_sha256"] if suite == "accuracy" else case["sha256"]
            reference = case["reference"] if suite == "accuracy" else reference_dir + "/" + cid + ".png" if cid in references and case["validity"] != "invalid" else None
            reference_hash = case["png_sha256"] if suite == "accuracy" else references[cid]["png_sha256"] if reference else None
            case_outputs = []
            rows = []
            images = []
            diffs = []
            for lib in LIBRARIES:
                key = suite + "/" + cid + "-" + lib
                row = _file(ctx, key + ".render.json")
                raster = _tree(ctx, key + ".render")
                identity = {"case": cid, "library": lib, "group": case["group"], "score": None}
                if suite != "accuracy":
                    identity["validity"] = case["validity"]
                spec = {"source": files[zpl].path, "sha256": digest, "width": case["width"], "height": case["height"], "row": identity, "timeout": 45 if suite == "accuracy" else 15}
                inputs = [files[zpl]]
                if lib == "labelary":
                    capture = captures.get((digest, case["width"], case["height"]))
                    if capture == None:
                        fail("Missing saved Labelary capture for %s; collect or record unavailable service evidence first" % cid)
                    spec["row"] = dict(identity, status = capture["status"], diagnostic = capture.get("diagnostic", ""), observed_utc = capture.get("received_utc", capture["requested_utc"]))
                    png = files["docs/benchmarks/labelary/" + capture["image"]] if capture["status"] == "rendered" else None
                    spec["saved"] = png.path if png else ""
                    if png:
                        spec["png_sha256"] = capture["png_sha256"]
                        inputs.append(png)
                else:
                    spec["library"] = compiled[lib].path
                    inputs.append(compiled[lib])
                _invoke(ctx, "render", key, spec, inputs, [row, raster])
                scored = _file(ctx, key + ".comparison.json")
                diff = _tree(ctx, key + ".diff")
                spec = {"suite": suite, "row": row.path, "image": raster.path}
                inputs = [row, raster]
                if reference:
                    spec.update(reference = files[reference].path, sha256 = reference_hash)
                    inputs.append(files[reference])
                _invoke(ctx, "compare", key + "-compare", spec, inputs, [scored, diff])
                case_outputs += [row, raster, scored, diff]
                rows.append(scored)
                compared.append(scored)
                rendered.append(row)
                images.append(raster)
                diffs.append(diff)

                # Each optional image tree has a single image.png. Assembly renames it.
                publish.extend([(raster, renders + "/images/" + cid + "-" + lib + ".png"), (diff, assets + "/images/" + cid + "-" + lib + "-diff.png")])
                if case.get("relation"):
                    group = (lib, case["relation"]["set"])
                    if group not in relation_groups:
                        relation_groups[group] = []
                    relation_groups[group].append((row, raster))
            frame = _file(ctx, suite + "/" + cid + ".viewport.json")
            visible = images + ([files[reference]] if reference else [])
            _invoke(ctx, "preview", suite + "/" + cid + "-viewport", {"mode": "frame", "images": [f.path for f in visible]}, visible, [frame])
            previews = [(images[i], LIBRARIES[i]) for i in range(len(LIBRARIES))] + [(diffs[i], LIBRARIES[i] + "-diff") for i in range(len(LIBRARIES))]
            if reference:
                previews.append((files[reference], "printer"))
            for image, suffix in previews:
                thumb = _tree(ctx, suite + "/" + cid + "-" + suffix + ".preview")
                _invoke(ctx, "preview", suite + "/" + cid + "-" + suffix + "-preview", {"mode": "preview", "image": image.path, "frame": frame.path}, [image, frame], [thumb])
                publish.append((thumb, assets + "/previews/" + cid + "-" + suffix + ".png"))
                case_outputs.append(thumb)
            page = _tree(ctx, suite + "/pages/" + cid)
            _invoke(ctx, "pages", suite + "/page-" + cid, {"mode": "case", "page": base + "/cases/" + cid + ".md", "base": base, "assets": assets, "renders": renders, "title": case["name"], "cases": [case], "libraries": LIBRARIES, "rows": [r.path for r in rows], "source": zpl, "reference": reference, "failure": failures.get(cid, {}).get("error")}, rows, [page])
            publish.append((page, ""))
            groups["case_" + suite + "_" + cid] = depset(case_outputs + [frame, page])
        for lib in LIBRARIES + ["index"]:
            rows = compared if lib == "index" else [compared[i] for i in range(len(compared)) if i % len(LIBRARIES) == LIBRARIES.index(lib)]
            page = _tree(ctx, suite + "/pages/library-" + lib)
            _invoke(ctx, "pages", suite + "/library-" + lib, {"mode": "index" if lib == "index" else "library", "page": base + ("/README.md" if lib == "index" else "/libraries/" + lib + ".md"), "base": base, "assets": assets, "title": suite + " comparisons" if lib == "index" else lib + " versus printer", "cases": cases, "rows": [r.path for r in rows], "libraries": LIBRARIES}, rows, [page])
            publish.append((page, ""))
        relations = []
        for (lib, group), entries in relation_groups.items():
            output = _file(ctx, suite + "/relations/" + lib + "-" + group + ".json")
            _invoke(ctx, "relation", suite + "/relation-" + lib + "-" + group, {"library": lib, "set": group, "rows": [r.path for r, _ in entries], "images": [i.path for _, i in entries]}, [f for pair in entries for f in pair], [output])
            relations.append(output)
        aggregate = _tree(ctx, suite + "/aggregate")
        metadata = {k: v for k, v in saved.items() if k not in ["cases", "results", "relations", "adapters", "host", "measured_utc"]}
        if suite == "accuracy":
            metadata["fresh_reference"] = {k: v for k, v in fresh.items() if k != "cases"}
            metadata["archived_reference"] = {k: v for k, v in archive.items() if k != "cases"}
        spec = {"suite": suite, "metadata": metadata, "cases": cases, "rows": [r.path for r in (compared if suite == "accuracy" else rendered)], "comparisons": [r.path for r in compared], "relations": [r.path for r in relations], "captured_utc": saved["measured_utc"], "renders": renders, "base": base, "libraries": {lib: f.path for lib, f in compiled.items()}}
        inputs = compared + rendered + relations
        if suite == "accuracy":
            inputs += compiled.values()
        else:
            manifest = corpus + "/manifest.json"
            reference_manifest = reference_dir + "/manifest.json"
            spec.update(manifest = files[manifest].path, manifest_name = manifest, reference_manifest = files[reference_manifest].path, reference_name = reference_manifest, coverage = {"cases": len(cases), "attempts": len(compared), "printer_references": len(references), "printer_unavailable": len(failures), "printer_excluded": len([c for c in cases if not c.get("capture_eligible", True)])})
            inputs += [files[manifest], files[reference_manifest]]
        _invoke(ctx, "aggregate", suite + "/aggregate", spec, inputs, [aggregate])
        aggregates.append((aggregate, ""))
        publish.append((aggregate, ""))

    # Each legacy report family runs independently, using the cached result documents.
    metric_scripts = ["benchmarks/accuracy/run.py", "benchmarks/accuracy/pixels.py", "benchmarks/accuracy/metrics.py"]
    plot_scripts = ["benchmarks/report.py", "benchmarks/formatting.py"]
    report_inputs = {
        "catalog": ["benchmarks/catalog.py", "benchmarks/templates/", "benchmarks/popularity.json", "benchmarks/sources.lock.json", "benchmarks/adapters/", "docs/benchmarks/results.json"] + plot_scripts,
        "support": ["benchmarks/support.py", "docs/benchmarks/command-support.json", "docs/zpl-command-index.tsv"] + plot_scripts,
        "performance": ["benchmarks/run.py", "docs/benchmarks/results.json", "docs/benchmarks/samples/"] + plot_scripts,
        "invalid": ["benchmarks/invalid.py", "test-data/invalid-zpl/", "docs/benchmarks/invalid/results.json"] + metric_scripts + plot_scripts,
        "labelary": ["benchmarks/labelary.py", "benchmarks/conformance.py", "test-data/render-conformance/", "test-data/external-zpl/", "benchmarks/accuracy/reference/", "references/", "docs/benchmarks/labelary/"] + metric_scripts + plot_scripts,
        "conformance-report": ["benchmarks/conformance.py", "test-data/render-conformance/"] + metric_scripts + plot_scripts,
        "external-report": ["benchmarks/conformance.py", "test-data/external-zpl/"] + metric_scripts + plot_scripts,
        "accuracy-report": ["benchmarks/accuracy/report.py", "benchmarks/accuracy/gallery.py", "benchmarks/accuracy/presentation.py"] + metric_scripts + plot_scripts,
        "compatibility": ["benchmarks/compatibility.py", "benchmarks/catalog.py", "benchmarks/sources.lock.json", "benchmarks/adapters/", "benchmarks/accuracy/reference/", "benchmarks/accuracy/conformance-reference/", "references/", "test-data/render-conformance/", "docs/zpl-command-index.tsv", "docs/benchmarks/argument-support.md", "docs/benchmarks/command-support.json", "docs/benchmarks/labelary/captures.json"] + metric_scripts + plot_scripts,
        "validate": ["build/validate.py", "benchmarks/conformance.py", "benchmarks/accuracy/cases.py", "benchmarks/accuracy/reference/", "benchmarks/accuracy/conformance-reference/", "benchmarks/accuracy/external-reference/", "references/", "test-data/", "docs/zpl-command-index.tsv"] + metric_scripts + plot_scripts,
    }
    for name, commands in [
        ("catalog", [["benchmarks/catalog.py"]]),
        ("support", [["benchmarks/support.py", "--reports-only"]]),
        ("performance", [["benchmarks/report.py", "docs/benchmarks", "markdown"]]),
        ("invalid", [["benchmarks/invalid.py", "--report-only"], ["benchmarks/invalid.py", "--check"]]),
        ("labelary", [["benchmarks/labelary.py"]]),
        ("conformance-report", [["benchmarks/conformance.py", "--reports-only", "--output", "docs/benchmarks/conformance"]]),
        ("external-report", [["benchmarks/conformance.py", "--reports-only", "--corpus", "test-data/external-zpl", "--output", "docs/benchmarks/external-zpl"]]),
        ("accuracy-report", [["benchmarks/accuracy/report.py", "docs/benchmarks/accuracy", "--no-gallery", "--part=markdown"]]),
        ("accuracy-chart", [["benchmarks/accuracy/report.py", "docs/benchmarks/accuracy", "--no-gallery", "--part=chart"]]),
        ("compatibility", [["benchmarks/compatibility.py"]]),
        ("validate", [["build/validate.py"]]),
    ]:
        selected = _select(files, report_inputs["accuracy-report" if name == "accuracy-chart" else name])
        if name == "conformance-report":
            selected += [aggregates[1]]
        elif name == "external-report":
            selected += [aggregates[2]]
        elif name in ["accuracy-report", "accuracy-chart"]:
            selected += [aggregates[0]]
        elif name == "compatibility":
            selected += aggregates[:2]
        output = _stage(ctx, name, selected, commands)
        publish.append((output, ""))
    measurements = CATALOG["docs/benchmarks/results.json"]
    for part in ["parse", "png", "generate", "memory", "size"]:
        data = {"results": [], "sizes": {}}
        if part == "size":
            data["sizes"] = {lib: {k: row[k] for k in ["bytes", "artifact_bytes"] if k in row} for lib, row in measurements["sizes"].items()}
        else:
            fields = ["status", "library", "peak_rss_bytes"] if part == "memory" else ["status", "library", "fixture", "mode", "median_ns", "min_ns", "max_ns"]
            data["results"] = [{k: row[k] for k in fields} for row in measurements["results"] if row["status"] == "ok" and (part == "memory" or row["mode"] == part)]
        source = _file(ctx, "plots/" + part + ".json")
        ctx.actions.write(source, json.encode(data))
        output = _stage(ctx, "plot-" + part, _select(files, plot_scripts) + [(source, "docs/benchmarks/results.json")], [["benchmarks/report.py", "docs/benchmarks", part]])
        publish.append((output, ""))
    result = _stage(ctx, "assemble", static + publish, [], assemble = True)
    return [DefaultInfo(files = depset([result])), OutputGroupInfo(**groups)]

pipeline = rule(implementation = _impl, attrs = dict({
    "srcs": attr.label_list(allow_files = True),
    "libraries": attr.label_list(),
}, **{"_" + name: attr.label(default = "//:action_" + name, executable = True, cfg = "exec") for name in ["render", "compare", "preview", "pages", "aggregate", "relation", "stage"]}))
