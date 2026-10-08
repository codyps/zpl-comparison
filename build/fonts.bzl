"""Deterministic shared font bundle, independent of renderer compilation."""

def _impl(ctx):
    output = ctx.actions.declare_directory(ctx.label.name)
    ctx.actions.run(
        executable = ctx.executable._builder,
        arguments = [output.path],
        tools = [ctx.attr._builder[DefaultInfo].files_to_run],
        outputs = [output],
        mnemonic = "ZplFonts",
    )
    return [DefaultInfo(files = depset([output]))]

comparison_fonts = rule(implementation = _impl, attrs = {
    "_builder": attr.label(default = "//:font_builder", executable = True, cfg = "exec"),
})
