"""Expose a pinned downloaded executable to language toolchains."""

def _executable_impl(ctx):
    output = ctx.actions.declare_file(ctx.label.name)
    ctx.actions.symlink(output = output, target_file = ctx.file.src, is_executable = True)
    return [DefaultInfo(executable = output)]

executable_file = rule(
    implementation = _executable_impl,
    executable = True,
    attrs = {"src": attr.label(allow_single_file = True, mandatory = True)},
)
