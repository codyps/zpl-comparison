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
        archive = name + ".zip" if name == "icu" else name + ".tar.gz" if name in ["go", "node", "dotnet", "wasm-bindgen"] else name + ".tar.xz"
        if "sha512" in pin:
            # Bazel accepts SRI SHA-512 as well as SHA-256.
            result = ctx.execute(["python3", "-c", "import base64,sys;print('sha512-'+base64.b64encode(bytes.fromhex(sys.argv[1])).decode())", pin["sha512"]])
            ctx.download(pin["url"], archive, integrity = result.stdout.strip())
        else:
            ctx.download(pin["url"], archive, sha256 = pin["sha256"])
        ctx.extract(archive, output = name + "-archive" if name in ["cargo", "rustc", "rust-std", "rust-wasm-std"] else name)
        ctx.delete(archive)
        if name in ["cargo", "rustc", "rust-std", "rust-wasm-std"]:
            root = ctx.path(name + "-archive").readdir()[0]
            _run(ctx, ["bash", str(root.get_child("install.sh")), "--prefix=" + str(ctx.path("rust")), "--disable-ldconfig"])
            ctx.delete(name + "-archive")
        elif name == "wasm-bindgen":
            _run(ctx, ["sh", "-c", "mv wasm-bindgen/wasm-bindgen-*/* wasm-bindgen/ && rmdir wasm-bindgen/wasm-bindgen-*/"])
        elif name == "go":
            _run(ctx, ["sh", "-c", "mv go/go/* go/ && rmdir go/go"])
        elif name == "node":
            _run(ctx, ["sh", "-c", "mv node/node-*/* node/ && rmdir node/node-*"])
    if "icu" in pins:
        ctx.read(ctx.attr.dotnet_runtime)  # The subprocess reads this toolchain input.
        _run(ctx, ["python3", str(ctx.path(ctx.attr.dotnet_runtime)),
                   str(ctx.path("dotnet")), str(ctx.path("icu")),
                   pins["icu"]["rid"], pins["icu"]["version"]])
        ctx.delete("icu")
    host = _run(ctx, ["sh", "-c", "uname -sm; cc --version; ld -v 2>&1 || true"])
    ctx.file("host.txt", host)
    dotnet_build = ctx.read(ctx.attr.dotnet_build).format(
        sdk = ctx.path("dotnet/sdk").readdir()[0].basename,
        runtime = ctx.path("dotnet/shared/Microsoft.NETCore.App").readdir()[0].basename,
        os = "osx" if os == "darwin" else "linux",
        cpu = "aarch64" if arch == "arm64" else "x86_64",
    )
    ctx.file("BUILD.bazel", dotnet_build + "\n" + "\n".join([
        'filegroup(name="%s", srcs=glob(["%s/**"]) + ["host.txt"])' % (n, n)
        for n in ["rust", "go", "node", "dotnet", "wasm-bindgen"]
    ]))

native_tools = repository_rule(implementation = _tools_impl, attrs = {
    "lock": attr.label(mandatory = True),
    "dotnet_runtime": attr.label(default = "//:build/dotnet_runtime.py"),
    "dotnet_build": attr.label(default = "//:build/dotnet_toolchain.BUILD"),
})

def _inputs_impl(ctx):
    files = {}
    for label in ctx.attr.manifests:
        p = ctx.path(label)
        # The subprocess reads these files; register their contents as fetch inputs.
        ctx.read(p)
        files[label.name] = str(p)
    tools = str(ctx.path(ctx.attr.tools).dirname)
    source = ctx.getenv("ZPL_SOURCE_PATH", "")
    _run(ctx, ["python3", str(ctx.path(ctx.attr.bootstrap)), ctx.attr.kind, tools, json.encode(files), source])
    build = 'package(default_visibility=["//visibility:public"])\nfilegroup(name="files",srcs=glob(["**"],exclude=["BUILD.bazel"]))\n'
    if ctx.attr.kind == "rust":
        for name, patterns in json.decode(ctx.read("groups.json")).items():
            build += 'filegroup(name=%s,srcs=glob(%s))\n' % (repr(name), repr(patterns))
    support = {
        "rust": ["vendor/labelize*/**", "vendor/zpl-forge*/**", "vendor/zpl-builder*/**", "benchmarks/_work/zpl/**"],
        "go": ["benchmarks/_work/go-zpl/**"],
        "codyps-zpl-node": ["benchmarks/_work/codyps-zpl-node/**"],
        "node": ["benchmarks/_work/zplr/**"],
        "zebrash": ["benchmarks/_work/zebrash/**"],
        "zpl-renderer-js": ["benchmarks/_work/zpl-renderer-js/**"],
        "zebrash-ts": ["benchmarks/_work/zebrash-ts/**"],
        "dotnet": ["benchmarks/_work/BinaryKits.Zpl/**"],
    }
    build += 'filegroup(name="support",srcs=glob(%s))\n' % repr(support[ctx.attr.kind])
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
    commands = {}
    for name in values["references/barcodes-zd621-v1/manifest.json"]["cases"]:
        source = ctx.read(Label("//:references/barcodes-zd621-v1/" + name + ".zpl"))
        codes = [part[:2] for part in source.split("^")[1:] if part.startswith("B") and part[:2] != "BY"]
        commands[name] = "^" + codes[0] if codes else "See ZPL"
    values["barcode_commands"] = commands
    inputs = {}
    for label in ctx.attr.inputs:
        ctx.read(label)
        inputs[label.name] = str(ctx.path(label))
    result = ctx.execute(["python3", str(ctx.path(ctx.attr.identity)), json.encode(inputs), "render", ctx.attr.python_version])
    if result.return_code:
        fail(result.stderr)
    values["render_inputs"] = json.decode(result.stdout)
    result = ctx.execute(["python3", str(ctx.path(ctx.attr.identity)), json.encode(inputs), "probe", ctx.attr.python_version])
    if result.return_code:
        fail(result.stderr)
    values["probe_inputs"] = json.decode(result.stdout)
    ctx.file("catalog.bzl", "CATALOG = json.decode(%s)\n" % repr(json.encode(values)))
    ctx.file("BUILD.bazel", 'exports_files(["catalog.bzl"])\n')

catalog = repository_rule(implementation = _catalog_impl, attrs = {
    "python_version": attr.string(mandatory = True),
    "manifests": attr.label_list(),
    "inputs": attr.label_list(),
    "identity": attr.label(default = "//:build/observation_inputs.py"),
})

def _baseline_impl(ctx):
    override = ctx.getenv("ZPL_BASELINE_LOCK", "")
    lock = json.decode(ctx.read(ctx.path(override) if override else ctx.attr.lock))
    ctx.download(lock["url"], "baseline.tar.gz", sha256 = lock["sha256"])
    ctx.extract("baseline.tar.gz", output = "archive", stripPrefix = lock["strip_prefix"])
    _run(ctx, ["python3", str(ctx.path(ctx.attr.prepare)), "--source", str(ctx.path("archive")), "--output", str(ctx.path("observations")), "--revision", lock["revision"]])
    ctx.delete("archive")
    ctx.delete("baseline.tar.gz")
    ctx.file("BUILD.bazel", 'package(default_visibility=["//visibility:public"])\nfilegroup(name="files",srcs=glob(["observations/**"]))\n')

observation_baseline = repository_rule(implementation = _baseline_impl, attrs = {
    "lock": attr.label(mandatory = True),
    "prepare": attr.label(default = "//:build/baseline.py"),
})

def _support_sources_impl(ctx):
    pins = json.decode(ctx.read(ctx.attr.lock))
    for name in ["zpl-toolchain", "python-zpl", "jszpl"]:
        dest = str(ctx.path("benchmarks/_work/" + name))
        _run(ctx, ["git", "init", "--initial-branch=main", dest])
        _run(ctx, ["git", "-C", dest, "fetch", "--depth=1", pins[name]["url"], pins[name]["rev"]])
        _run(ctx, ["git", "-C", dest, "checkout", "--detach", "FETCH_HEAD"])
        if _run(ctx, ["git", "-C", dest, "rev-parse", "HEAD"]).strip() != pins[name]["rev"]:
            fail("Support source revision mismatch: " + name)
        ctx.delete(dest + "/.git")
    ctx.file("BUILD.bazel", 'package(default_visibility=["//visibility:public"])\nfilegroup(name="files",srcs=glob(["benchmarks/**"]))\n')

support_sources = repository_rule(implementation = _support_sources_impl, attrs = {"lock": attr.label(mandatory = True)})


def _host_impl(ctx):
    info = _run(ctx, ["sh", "-c", "uname -smr; cc --version; ld -v 2>&1 || true; if command -v xcrun >/dev/null; then xcrun --show-sdk-version; xcrun --show-sdk-build-version; else ldd --version; fi"])
    ctx.file("identity.txt", info)
    ctx.file("BUILD.bazel", 'exports_files(["identity.txt"],visibility=["//visibility:public"])\n')

native_host = repository_rule(implementation = _host_impl, local = True)
