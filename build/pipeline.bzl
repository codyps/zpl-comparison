"""Fine-grained report action graph; no rendering in report assembly."""

load("@report_catalog//:catalog.bzl", "CATALOG")
load("//:build/zq610.bzl", "zq610_matrix")
load("//:build/evaluations.bzl", "invalid_matrix")
load("//:build/campaigns.bzl", "campaigns")

LIBRARIES = ["codyps-zpl", "labelize", "forge", "go", "ffi", "binarykits", "zplr", "zebrash", "zpl-renderer-js", "zebrash-ts", "labelary"]

def _invoke(ctx, kind, name, spec, inputs, outputs):
    if kind == "pages" and ctx.attr.saved:
        spec = dict(spec, saved = True)
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
        use_default_shell_env = True,
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

def _observation(ctx, key, lib, spec, files, compiled, baseline, captures, row, raster):
    inputs = [files[spec.pop("source_name")]] if "source_name" in spec else [f for f in files.values() if f.path == spec["source"]]
    kind = "saved" if ctx.attr.saved else "render"
    if lib == "labelary":
        capture = captures.get((spec["sha256"], spec["width"], spec["height"]))
        spec["saved"] = ""
        spec["row"].update(status = "not_captured", diagnostic = "No captured Labelary observation for this input and canvas")
        if capture:
            spec["row"].update(status = capture["status"], diagnostic = capture.get("diagnostic", ""), observed_utc = capture.get("received_utc", capture.get("requested_utc", "unknown")))
            if capture["status"] == "rendered":
                image = files[capture.get("image_root", "docs/benchmarks/labelary/") + capture["image"]]
                spec.update(saved = image.path, png_sha256 = capture["png_sha256"])
                inputs.append(image)
    elif ctx.attr.saved:
        evidence = baseline.get("rows/" + key + ".json")
        image = baseline.get("images/" + key + ".png")
        expected = {"source_sha256": spec["sha256"], "requested_dimensions": [spec["width"], spec["height"]],
                    "render_profile": spec.get("render_profile", "zd621-203dpi"), "input_identity": CATALOG["render_inputs"][lib],
                    "timeout_seconds": spec.get("timeout", 45)}
        spec = {"row": spec["row"], "expected": expected, "evidence": evidence.path if evidence else None, "image": image.path if image else None}
        inputs = ([evidence] if evidence else []) + ([image] if image else [])
    else:
        spec.update(library = compiled[lib].path, input_identity = CATALOG["render_inputs"][lib])
        inputs.append(compiled[lib])
    _invoke(ctx, kind, key, spec, inputs, [row, raster])

def _impl(ctx):
    files = {f.short_path: f for f in ctx.files.srcs}
    compiled = {name: target[DefaultInfo].files.to_list()[0] for name, target in zip(LIBRARIES[:-1], ctx.attr.libraries)}
    baseline = {"/".join(f.short_path.split("/")[3:]): f for f in ctx.files.baseline}
    captures = {(r["sha256"], r["width"], r["height"]): r for r in CATALOG["docs/benchmarks/labelary/captures.json"]["cases"]}
    publish = []
    aggregates = []
    groups = {}

    # Maintained documents, captured evidence, and scripts remain downloadable.
    static = [(f, p) for p, f in files.items() if not (p.startswith("docs/benchmarks/") and (("/images/" in p and not p.startswith("docs/benchmarks/labelary/")) or p in ["docs/benchmarks/" + s + "/results.json" for s in ["accuracy", "conformance", "external-zpl", "layout-accuracy"]]))]
    for suite in ["accuracy", "conformance", "external-zpl", "layout-accuracy"]:
        suite_start = len(publish)
        libraries = LIBRARIES
        renders = "docs/benchmarks/" + suite
        base = "docs/benchmarks/accuracy/comparisons" + ("" if suite == "accuracy" else "/features" if suite == "conformance" else "/layout" if suite == "layout-accuracy" else "/external")
        assets = renders if suite == "accuracy" else base
        corpus = "test-data/render-conformance" if suite == "conformance" else "test-data/layout-accuracy" if suite == "layout-accuracy" else "test-data/external-zpl"
        cases = [] if suite == "accuracy" else CATALOG[corpus + "/manifest.json"]["cases"]
        reference_dir = "benchmarks/accuracy/" + ("conformance-reference" if suite == "conformance" else "layout-reference" if suite == "layout-accuracy" else "external-reference")
        references = {} if suite == "accuracy" else {r["name"]: r for r in CATALOG[reference_dir + "/manifest.json"]["cases"]}
        failures = {} if suite == "accuracy" else {r["name"]: r for r in CATALOG[reference_dir + "/manifest.json"].get("failures", [])}
        if suite == "accuracy":
            fresh = CATALOG["benchmarks/accuracy/reference/manifest.json"]
            archive = CATALOG["references/barcodes-zd621-v1/manifest.json"]
            cases = [dict(c, id = "argument-" + c["name"], source = "fresh arguments", zpl = "benchmarks/accuracy/reference/" + c["name"] + ".zpl", reference = "benchmarks/accuracy/reference/" + c["name"] + ".png") for c in fresh["cases"] if c["group"] != "repeatability"]
            for name, c in archive["cases"].items():
                cases.append(dict(id = "barcode-" + name, name = name, group = "barcode-formats", command = CATALOG["barcode_commands"][name], arguments = "See exact archived ZPL", width = archive["width"], height = 1218, source = "archived barcode development corpus", zpl = "references/barcodes-zd621-v1/" + name + ".zpl", reference = "references/barcodes-zd621-v1/" + name + ".png", zpl_sha256 = c["zpl_sha256"], png_sha256 = c["printer_png_sha256"]))
        compared = []
        rendered = []
        relation_groups = {}
        for case in cases:
            cid = case.get("id", case["name"])
            zpl = case["zpl"] if suite == "accuracy" else corpus + "/" + case["file"]
            digest = case["zpl_sha256"] if suite == "accuracy" else case["sha256"]
            reference = case["reference"] if suite == "accuracy" else reference_dir + "/" + cid + ".png" if cid in references and case["validity"] != "invalid" and not case.get("reference_unscored_reason") else None
            reference_hash = case["png_sha256"] if suite == "accuracy" else references[cid]["png_sha256"] if reference else None
            case_outputs = []
            rows = []
            images = []
            diffs = []
            for lib in libraries:
                key = suite + "/" + cid + "-" + lib
                row = _file(ctx, key + ".render.json")
                raster = _tree(ctx, key + ".render")
                identity = {"case": cid, "library": lib, "group": case["group"], "score": None}
                if suite != "accuracy":
                    identity["validity"] = case["validity"]
                    if case.get("reference_unscored_reason"):
                        identity["comparison_diagnostic"] = case["reference_unscored_reason"]
                spec = {"source": files[zpl].path, "source_name": zpl, "sha256": digest, "width": case["width"], "height": case["height"], "row": identity, "timeout": 45 if suite == "accuracy" else 15}
                inputs = [files[zpl]]
                _observation(ctx, key, lib, spec, files, compiled, baseline, captures, row, raster)
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
            previews = [(images[i], libraries[i]) for i in range(len(libraries))] + [(diffs[i], libraries[i] + "-diff") for i in range(len(libraries))]
            if reference:
                previews.append((files[reference], "printer"))
            for image, suffix in previews:
                thumb = _tree(ctx, suite + "/" + cid + "-" + suffix + ".preview")
                _invoke(ctx, "preview", suite + "/" + cid + "-" + suffix + "-preview", {"mode": "preview", "image": image.path, "frame": frame.path}, [image, frame], [thumb])
                publish.append((thumb, assets + "/previews/" + cid + "-" + suffix + ".png"))
                case_outputs.append(thumb)
            page = _tree(ctx, suite + "/pages/" + cid)
            _invoke(ctx, "pages", suite + "/page-" + cid, {"mode": "case", "suite": suite, "page": base + "/cases/" + cid + ".md", "base": base, "assets": assets, "renders": renders, "title": case["name"], "cases": [case], "libraries": libraries, "rows": [r.path for r in rows], "source": zpl, "reference": reference, "failure": failures.get(cid, {}).get("error")}, rows, [page])
            publish.append((page, ""))
            groups["case_" + suite + "_" + cid] = depset(case_outputs + [frame, page])
        for lib in libraries + ([] if suite == "accuracy" else ["index"]):
            rows = compared if lib == "index" else [compared[i] for i in range(len(compared)) if i % len(libraries) == libraries.index(lib)]
            page = _tree(ctx, suite + "/pages/library-" + lib)
            _invoke(ctx, "pages", suite + "/library-" + lib, {"mode": "index" if lib == "index" else "library", "suite": suite, "page": base + ("/README.md" if lib == "index" else "/libraries/" + lib + ".md"), "base": base, "assets": assets, "title": suite + " comparisons" if lib == "index" else lib + " versus printer", "cases": cases, "rows": [r.path for r in rows], "libraries": libraries}, rows, [page])
            publish.append((page, ""))
        relations = []
        for (lib, group), entries in relation_groups.items():
            output = _file(ctx, suite + "/relations/" + lib + "-" + group + ".json")
            _invoke(ctx, "relation", suite + "/relation-" + lib + "-" + group, {"library": lib, "set": group, "rows": [r.path for r, _ in entries], "images": [i.path for _, i in entries]}, [f for pair in entries for f in pair], [output])
            relations.append(output)
        aggregate = _tree(ctx, suite + "/aggregate")
        metadata = {"schema": 1, "threshold": 128}
        if suite != "accuracy":
            metadata.update(suite = CATALOG[corpus + "/manifest.json"]["suite"], references = CATALOG[reference_dir + "/manifest.json"])
        if suite == "accuracy":
            metadata["fresh_reference"] = {k: v for k, v in fresh.items() if k != "cases"}
            metadata["archived_reference"] = {k: v for k, v in archive.items() if k != "cases"}
        spec = {"suite": suite, "metadata": metadata, "cases": cases, "rows": [r.path for r in (compared if suite in ["accuracy", "layout-accuracy"] else rendered)], "comparisons": [r.path for r in compared], "relations": [r.path for r in relations], "captured_utc": "unavailable", "renders": renders, "base": base, "libraries": {lib: f.path for lib, f in compiled.items()}}
        inputs = compared + rendered + relations
        if ctx.attr.saved:
            spec["saved_provenance"] = {"host": "Saved trusted observations; see individual provenance"}
            if suite == "accuracy":
                spec["saved_adapters"] = baseline["adapters.json"].path
                inputs.append(baseline["adapters.json"])
        if suite == "accuracy":
            inputs += compiled.values()
        else:
            manifest = corpus + "/manifest.json"
            reference_manifest = reference_dir + "/manifest.json"
            spec.update(manifest = files[manifest].path, manifest_name = manifest, reference_manifest = files[reference_manifest].path, reference_name = reference_manifest, coverage = {"cases": len(cases), "attempts": len(compared), "printer_references": len([c for c in cases if c["name"] in references and c["validity"] != "invalid"]), "printer_unavailable": len(failures), "printer_excluded": len([c for c in cases if not c.get("capture_eligible", True)])})
            inputs += [files[manifest], files[reference_manifest]]
        _invoke(ctx, "aggregate", suite + "/aggregate", spec, inputs, [aggregate])
        aggregates.append((aggregate, ""))
        publish.append((aggregate, ""))
        groups["suite_" + suite] = depset([f for f, _ in publish[suite_start:]])

    invalid = invalid_matrix(ctx, files, compiled, baseline, CATALOG, _invoke, _stage, _select)
    publish.append((invalid, ""))
    groups["suite_invalid"] = depset([invalid])
    support_inputs = _select(files, ["benchmarks/support.py", "benchmarks/report.py", "benchmarks/formatting.py", "benchmarks/sources.lock.json", "docs/zpl-command-index.tsv"])
    if ctx.attr.saved:
        support_inputs.append((baseline["reports/docs/benchmarks/command-support.json"], "docs/benchmarks/command-support.json"))
        support_command = ["benchmarks/support.py", "--reports-only"]
    else:
        support_inputs += [(f, "/".join(f.short_path.split("/")[2:])) for f in ctx.files.support_inputs]
        support_command = ["benchmarks/support.py", "--vendor", "vendor"]
    support = _stage(ctx, "support", support_inputs, [support_command])
    publish.append((support, ""))
    if ctx.attr.saved:
        publish.append((baseline["reports/docs/benchmarks/command-support.json"], "docs/benchmarks/command-support.json"))
        publish.append((baseline["reports/benchmarks/popularity.json"], "benchmarks/popularity.json"))
    groups["suite_support"] = depset([support])

    public, paired, campaign_images = campaigns(ctx, files, compiled, baseline, CATALOG, LIBRARIES, _observation, _invoke, _stage, _select)
    publish += [(public, ""), (paired, "")] + campaign_images
    groups["suite_public"] = depset([public] + [f for f, p in campaign_images if p.startswith("docs/public")])
    groups["suite_paired"] = depset([paired] + [f for f, p in campaign_images if p.startswith("docs/benchmarks/zq610-plus/")])

    # Report generation consumes current observations without executing adapters.
    metric_scripts = ["benchmarks/accuracy/run.py", "benchmarks/accuracy/pixels.py", "benchmarks/accuracy/metrics.py"]
    plot_scripts = ["benchmarks/report.py", "benchmarks/formatting.py"]
    report_inputs = {
        "catalog": ["benchmarks/catalog.py", "benchmarks/templates/", "benchmarks/popularity.json", "benchmarks/sources.lock.json", "benchmarks/adapters/"] + plot_scripts,
        "support": ["benchmarks/support.py", "docs/zpl-command-index.tsv"] + plot_scripts,
        "labelary": ["benchmarks/labelary.py", "benchmarks/conformance.py", "test-data/render-conformance/", "test-data/public-zpl/", "test-data/external-zpl/", "test-data/layout-accuracy/", "benchmarks/accuracy/reference/", "references/", "docs/benchmarks/labelary/"] + metric_scripts + plot_scripts,
        "conformance-report": ["benchmarks/conformance.py", "test-data/render-conformance/"] + metric_scripts + plot_scripts,
        "layout-report": ["benchmarks/conformance.py", "test-data/layout-accuracy/"] + metric_scripts + plot_scripts,
        "external-report": ["benchmarks/conformance.py", "test-data/external-zpl/"] + metric_scripts + plot_scripts,
        "accuracy-report": ["benchmarks/accuracy/report.py", "benchmarks/accuracy/gallery.py", "benchmarks/accuracy/presentation.py"] + metric_scripts + plot_scripts,
        "compatibility": ["benchmarks/compatibility.py", "benchmarks/catalog.py", "benchmarks/sources.lock.json", "benchmarks/adapters/", "benchmarks/accuracy/reference/", "benchmarks/accuracy/conformance-reference/", "references/", "test-data/render-conformance/", "docs/zpl-command-index.tsv", "docs/benchmarks/argument-support.md", "docs/benchmarks/labelary/captures.json"] + metric_scripts + plot_scripts,
        "validate": ["build/validate.py", "benchmarks/public_examples.py", "benchmarks/labelary.py", "docs/benchmarks/labelary/", "docs/public-examples/", "benchmarks/conformance.py", "benchmarks/accuracy/cases.py", "benchmarks/accuracy/reference/", "benchmarks/accuracy/conformance-reference/", "benchmarks/accuracy/external-reference/", "benchmarks/accuracy/layout-reference/", "references/", "test-data/", "docs/zpl-command-index.tsv"] + metric_scripts + plot_scripts,
    }
    accuracy_report = None
    for name, commands in [
        ("catalog", [["benchmarks/catalog.py"]]),
        ("labelary", [["benchmarks/labelary.py"]]),
        ("conformance-report", [["benchmarks/conformance.py", "--reports-only", "--output", "docs/benchmarks/conformance"]]),
        ("layout-report", [["benchmarks/conformance.py", "--reports-only", "--corpus", "test-data/layout-accuracy", "--output", "docs/benchmarks/layout-accuracy"]]),
        ("external-report", [["benchmarks/conformance.py", "--reports-only", "--corpus", "test-data/external-zpl", "--output", "docs/benchmarks/external-zpl"]]),
        ("accuracy-report", [["benchmarks/accuracy/report.py", "docs/benchmarks/accuracy", "--no-gallery", "--part=markdown"]]),
        ("accuracy-chart", [["benchmarks/accuracy/report.py", "docs/benchmarks/accuracy", "--no-gallery", "--part=chart"]]),
        ("compatibility", [["benchmarks/compatibility.py"]]),
        ("validate", [["build/validate.py"]]),
    ]:
        selected = _select(files, report_inputs["accuracy-report" if name == "accuracy-chart" else name])
        if name == "catalog" and ctx.attr.saved:
            selected.append((baseline["reports/benchmarks/popularity.json"], "benchmarks/popularity.json"))
        if name == "conformance-report":
            selected += [aggregates[1]]
        elif name == "layout-report":
            selected += [aggregates[3]]
        elif name == "external-report":
            selected += [aggregates[2]]
        elif name in ["accuracy-report", "accuracy-chart"]:
            selected += [aggregates[0]]
        elif name == "validate":
            selected += _select(files, ["benchmarks/campaigns.py", "benchmarks/paired_labelary.py"]) + [(public, ""), (paired, "")] + campaign_images
        elif name == "compatibility":
            selected += aggregates[:2] + [(support, "")]
            if ctx.attr.saved:
                selected.append((baseline["reports/docs/benchmarks/command-support.json"], "docs/benchmarks/command-support.json"))
        output = _stage(ctx, name, selected, commands)
        if name == "accuracy-report":
            accuracy_report = output
        publish.append((output, ""))
    overview = _stage(ctx, "accuracy-overview", _select(files, ["benchmarks/accuracy/overview.py"]) + aggregates + [(accuracy_report, "")], [["benchmarks/accuracy/overview.py", "docs/benchmarks/accuracy"]])
    publish.append((overview, ""))
    candidate_outputs = zq610_matrix(ctx, files, compiled, baseline, CATALOG, LIBRARIES, _observation, _invoke, _stage)
    publish.extend(candidate_outputs)
    groups["suite_zq610_candidates"] = depset([f for f, _ in candidate_outputs])
    failures = _stage(ctx, "failure-inventory", _select(files, ["benchmarks/audit_failures.py"]) + aggregates + candidate_outputs + [(public, ""), (paired, "")],
                      [["benchmarks/audit_failures.py", "--input", ".", "--output", "docs/total-failures.json"]])
    publish.append((failures, ""))
    decoder = _stage(ctx, "barcode-decoder", _select(files, ["benchmarks/audit_public_barcodes.py", "references/public-zd621-20261002/", "docs/benchmarks/labelary/"]) + [(public, "")] + campaign_images,
                     [["benchmarks/audit_public_barcodes.py"]])
    publish.append((decoder, ""))
    result = _stage(ctx, "assemble", static + publish, [["benchmarks/accuracy/overview.py", "docs/benchmarks/accuracy", "--check"]], assemble = True)
    return [DefaultInfo(files = depset([result])), OutputGroupInfo(**groups)]

pipeline = rule(implementation = _impl, attrs = dict({
    "srcs": attr.label_list(allow_files = True),
    "saved": attr.bool(default = False),
    "baseline": attr.label_list(allow_files = True),
    "libraries": attr.label_list(),
    "support_inputs": attr.label_list(allow_files = True),
}, **{"_" + name: attr.label(default = "//:action_" + name, executable = True, cfg = "exec") for name in ["render", "compare", "preview", "pages", "aggregate", "relation", "saved", "probe", "stage"]}))
