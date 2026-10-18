"""Use the existing net10.0 NuGet lock with rules_dotnet's package rules."""
load("@rules_dotnet//dotnet:defs.bzl", "nuget_repo")

def _repository(ctx, name, directory):
    packages = json.decode(ctx.read(Label("//:benchmarks/adapters/" + directory + "/packages.lock.json")))["dependencies"]["net10.0"]
    integrity = json.decode(ctx.read(Label("//:benchmarks/adapters/" + directory + "/nuget-integrity.json")))
    nuget_repo(
        name = name,
        packages = [dict(
            name = name,
            id = name,
            version = package["resolved"],
            # NuGet contentHash excludes signing metadata; Bazel verifies the
            # complete downloaded archive with this separate raw SHA-512 pin.
            sha512 = integrity[name.lower() + "." + package["resolved"].lower() + ".nupkg"],
            sources = ["https://api.nuget.org/v3/index.json"],
            dependencies = {"net10.0": package.get("dependencies", {}).keys()},
            targeting_pack_overrides = [],
            framework_list = [],
        ) for name, package in packages.items()],
    )

def _nuget_impl(ctx):
    _repository(ctx, "comparison_nuget", "dotnet")
    _repository(ctx, "neodynamic_nuget", "neodynamic")
    return ctx.extension_metadata(reproducible = True)

nuget = module_extension(implementation = _nuget_impl)
