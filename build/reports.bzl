"""Offline reports as one cached action with a directory output."""

def _reports_impl(ctx):
    output = ctx.actions.declare_directory(ctx.label.name)
    manifest = ctx.actions.declare_file(ctx.label.name + ".inputs.json")
    ctx.actions.write(manifest, json.encode([
        [f.path, f.short_path]
        for f in ctx.files.srcs
    ]))
    ctx.actions.run(
        executable = ctx.executable._runner,
        arguments = [manifest.path, output.path],
        inputs = depset(ctx.files.srcs + [manifest]),
        tools = [ctx.attr._runner[DefaultInfo].files_to_run],
        outputs = [output],
        mnemonic = "ZplReports",
        progress_message = "Generating offline ZPL reports",
        env = {"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1", "MPLBACKEND": "Agg"},
    )
    return [DefaultInfo(files = depset([output]))]

reports = rule(
    implementation = _reports_impl,
    attrs = {
        "srcs": attr.label_list(allow_files = True),
        "_runner": attr.label(default = "//:report_runner", executable = True, cfg = "exec"),
    },
)
