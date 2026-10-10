"""Behavioral evaluations independent of rendering reports and printer scoring."""

def invalid_matrix(ctx, files, compiled, baseline, catalog, invoke, stage, select):
    lanes = {name: ["parse", "render"] for name in ["codyps-zpl", "labelize", "forge", "go", "binarykits", "zplr", "zebrash", "zebrash-ts"]}
    lanes["ffi"] = ["render"]
    lanes["codyps-zpl-node"] = ["render"]
    lanes["codyps-zpl-go"] = ["render"]
    lanes["zpl-renderer-js"] = ["render"]
    rows = []
    for case in catalog["test-data/invalid-zpl/manifest.json"]["cases"]:
        for lib, modes in lanes.items():
            for mode in modes:
                name = case["id"] + "-" + lib + "-" + mode
                output = ctx.actions.declare_file(ctx.label.name + "_actions/invalid/" + name + ".probe.json")
                sources = {variant: files["test-data/invalid-zpl/" + case[variant]["file"]] for variant in ["control", "invalid"]}
                inputs = sources.values()
                spec = {"case": case, "library": lib, "mode": mode, "repeats": 2, "timeout": 10,
                        "input_identity": catalog["probe_inputs"][lib], "sources": {k: f.path for k, f in sources.items()}}
                if ctx.attr.saved:
                    evidence = baseline.get("probes/" + name + ".json")
                    spec["baseline"] = evidence.path if evidence else None
                    inputs += [evidence] if evidence else []
                else:
                    spec["deployment"] = compiled[lib].path
                    inputs.append(compiled[lib])
                invoke(ctx, "probe", "invalid/" + name, spec, inputs, [output])
                rows.append((output, "_invalid_rows/" + name + ".json"))
    inputs = select(files, ["benchmarks/invalid.py", "benchmarks/report.py", "benchmarks/formatting.py", "benchmarks/accuracy/", "test-data/invalid-zpl/", "build/invalid_report.py"])
    return stage(ctx, "invalid-report", inputs + rows, [["build/invalid_report.py"]])
