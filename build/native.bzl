"""An independently cacheable compilation/deployment action per library."""

def _native_impl(ctx):
    output = ctx.actions.declare_directory(ctx.label.name)
    manifest = ctx.actions.declare_file(ctx.label.name + ".json")
    files = []
    dependency_files = []
    for f in ctx.files.deps:
        # External downloaded dependencies retain paths relative to their repository.
        relative = "/".join(f.short_path.split("/")[2:])
        # Download verification has already checked go.sum. Its moving sumdb
        # checkpoint and user-home state are not inputs to offline compilation.
        if ctx.attr.library in ["go", "go-native", "zebrash"] and any([
            relative.startswith(p)
            for p in ["go-home/", "home/", "modules/cache/download/sumdb/"]
        ]):
            continue
        if ctx.attr.library == "go-native" and relative.startswith("benchmarks/adapters/"):
            continue
        dependency_files.append(f)
        if relative.startswith("manifests/"):
            relative = "benchmarks/adapters/rust/" + relative.split("/")[-1]
        files.append([f.path, relative])
    files.extend([[f.path, f.short_path] for f in ctx.files.srcs])
    tools = ctx.files.toolchain
    root = tools[0].path.split("/rust/")[0].split("/go/")[0].split("/node/")[0].split("/dotnet/")[0]

    # host.txt may be the first input.
    if root.endswith("/host.txt"):
        root = root[:-len("/host.txt")]
    native = ctx.files.native
    ctx.actions.write(manifest, json.encode({"library": ctx.attr.library, "inputs": files, "tools": root, "native": native[0].path if native else ""}))
    ctx.actions.run(
        executable = ctx.executable._runner,
        arguments = [manifest.path, output.path],
        inputs = depset(ctx.files.srcs + dependency_files + tools + native + ctx.files._host + [manifest]),
        tools = [ctx.attr._runner[DefaultInfo].files_to_run],
        outputs = [output],
        mnemonic = "ZplLibraryBuild",
        progress_message = "Building pinned %s library" % ctx.attr.library,
        use_default_shell_env = True,
        execution_requirements = {"no-remote-exec": "1"},
    )
    return [DefaultInfo(files = depset([output]))]

native_library = rule(implementation = _native_impl, attrs = {
    "library": attr.string(mandatory = True),
    "srcs": attr.label_list(allow_files = True),
    "deps": attr.label_list(allow_files = True),
    "toolchain": attr.label_list(allow_files = True),
    "native": attr.label(allow_files = True),
    "_host": attr.label(default = "@native_host//:identity.txt", allow_files = True),
    "_runner": attr.label(default = "//:native_builder", executable = True, cfg = "exec"),
})
