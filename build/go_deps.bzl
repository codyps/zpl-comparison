"""Gazelle repositories with each renderer's existing Go module versions."""
load("@gazelle//:deps.bzl", "go_repository")

def _repo_name(group, module):
    return group + "_" + module.lower().replace("/", "_").replace(".", "_").replace("-", "_")

def _go_impl(ctx):
    pin = json.decode(ctx.read(Label("//:benchmarks/sources.lock.json")))["go-zpl"]
    for group, manifest in [
        ("go", Label("//:benchmarks/adapters/go/go.mod")),
        ("gonative", Label("@go_inputs//:benchmarks/_work/go-zpl/go.mod")),
        ("zebrash", Label("//:benchmarks/adapters/zebrash/go.mod")),
    ]:
        versions = {}
        for line in ctx.read(manifest).splitlines():
            words = [w for w in line.replace("require ", "").replace("\t", " ").strip().split(" ") if w]
            if len(words) >= 2 and words[1].startswith("v") and "." in words[0]:
                versions[words[0]] = words[1]
        sums = {}
        for line in ctx.read(manifest.relative(":" + manifest.name[:-3] + "sum")).splitlines():
            words = [w for w in line.replace("\t", " ").split(" ") if w]
            if len(words) == 3:
                sums[(words[0], words[1])] = words[2]
        if group != "zebrash":
            versions["github.com/StirlingMarketingGroup/go-zpl"] = "source"
        directives = ["gazelle:go_naming_convention go_default_library", "gazelle:proto disable_global", "gazelle:go_visibility //visibility:public"]
        for module in versions:
            repo = _repo_name(group, module)
            directives.extend([
                "gazelle:resolve go %s @%s//:go_default_library" % (module, repo),
                "gazelle:resolve_regexp go ^%s/(.*)$ @%s//$1:go_default_library" % (module.replace(".", "\\."), repo),
            ])
        for module, version in versions.items():
            attrs = dict(
                name = _repo_name(group, module),
                importpath = module,
                build_config = "//:build/go-repositories.WORKSPACE",
                build_directives = directives,
                build_naming_convention = "go_default_library",
                build_file_generation = "on",
            )
            if version == "source":
                attrs.update(remote = pin["url"], commit = pin["rev"], vcs = "git")
            else:
                attrs.update(version = version, sum = sums[(module, version)])
            go_repository(**attrs)
    return ctx.extension_metadata(reproducible = True)

go_deps = module_extension(implementation = _go_impl)
