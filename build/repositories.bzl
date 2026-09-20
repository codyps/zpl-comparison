"""Pinned native toolchains, dependency downloads, and analysis-time case catalog."""

def _run(ctx, args, env = {}):
    result = ctx.execute(args, environment = env, timeout = 1800, quiet = False)
    if result.return_code:
        fail("Command failed: %s\n%s" % (args, result.stderr))
    return result.stdout

def _tools_impl(ctx):
    arch = "arm64" if ctx.os.arch in ["aarch64", "arm64"] else "amd64"
    os = "darwin" if ctx.os.name == "mac os x" else "linux"
    pins = json.decode(ctx.read(ctx.attr.lock))[os + "-" + arch]
    for name, pin in pins.items():
        archive = name + ".tar.gz" if name in ["go", "node", "dotnet"] else name + ".tar.xz"
        if "sha512" in pin:
            # Bazel accepts SRI SHA-512 as well as SHA-256.
            result = ctx.execute(["python3", "-c", "import base64,sys;print('sha512-'+base64.b64encode(bytes.fromhex(sys.argv[1])).decode())", pin["sha512"]])
            ctx.download(pin["url"], archive, integrity = result.stdout.strip())
        else:
            ctx.download(pin["url"], archive, sha256 = pin["sha256"])
        ctx.extract(archive, output = name + "-archive" if name in ["cargo", "rustc", "rust-std"] else name)
        ctx.delete(archive)
        if name in ["cargo", "rustc", "rust-std"]:
            root = ctx.path(name + "-archive").readdir()[0]
            _run(ctx, ["bash", str(root.get_child("install.sh")), "--prefix=" + str(ctx.path("rust")), "--disable-ldconfig"])
            ctx.delete(name + "-archive")
        elif name == "go":
            _run(ctx, ["sh", "-c", "mv go/go/* go/ && rmdir go/go"])
        elif name == "node":
            _run(ctx, ["sh", "-c", "mv node/node-*/* node/ && rmdir node/node-*"])
    host = _run(ctx, ["sh", "-c", "uname -sm; cc --version; ld -v 2>&1 || true"])
    ctx.file("host.txt", host)
    ctx.file("BUILD.bazel", '\n'.join([
        'package(default_visibility = ["//visibility:public"])',
    ] + ['filegroup(name="%s", srcs=glob(["%s/**"]) + ["host.txt"])' % (n, n) for n in ["rust", "go", "node", "dotnet"]]))

native_tools = repository_rule(implementation = _tools_impl, attrs = {"lock": attr.label(mandatory = True)})

def _inputs_impl(ctx):
    files = {}
    for label in ctx.attr.manifests:
        p = ctx.path(label)
        files[label.name] = str(p)
    tools = str(ctx.path(ctx.attr.tools).dirname)
    source = ctx.getenv("ZPL_SOURCE_PATH", "")
    _run(ctx, ["python3", str(ctx.path(ctx.attr.bootstrap)), ctx.attr.kind, tools, json.encode(files), source])
    build = 'package(default_visibility=["//visibility:public"])\nfilegroup(name="files",srcs=glob(["**"],exclude=["BUILD.bazel"]))\n'
    if ctx.attr.kind == "rust":
        for name, patterns in json.decode(ctx.read("groups.json")).items():
            build += 'filegroup(name=%s,srcs=glob(%s))\n' % (repr(name), repr(patterns))
    ctx.file("BUILD.bazel", build)

native_inputs = repository_rule(
    implementation = _inputs_impl,
    attrs = {
        "kind": attr.string(mandatory = True),
        "tools": attr.label(default = "@native_tools//:host.txt"),
        "bootstrap": attr.label(default = "//:build/bootstrap.py"),
        "manifests": attr.label_list(),
    },
)

def _catalog_impl(ctx):
    values = {label.name: json.decode(ctx.read(label)) for label in ctx.attr.manifests}
    ctx.file("catalog.bzl", "CATALOG = json.decode(%s)\n" % repr(json.encode(values)))
    ctx.file("BUILD.bazel", 'exports_files(["catalog.bzl"])\n')

catalog = repository_rule(implementation = _catalog_impl, attrs = {"manifests": attr.label_list()})


def _host_impl(ctx):
    info = _run(ctx, ["sh", "-c", "uname -smr; cc --version; ld -v 2>&1 || true; if command -v xcrun >/dev/null; then xcrun --show-sdk-version; xcrun --show-sdk-build-version; else ldd --version; fi"])
    ctx.file("identity.txt", info)
    ctx.file("BUILD.bazel", 'exports_files(["identity.txt"],visibility=["//visibility:public"])\n')

native_host = repository_rule(implementation = _host_impl, local = True)
