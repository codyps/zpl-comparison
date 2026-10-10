"""Use the existing net10.0 NuGet lock with rules_dotnet's package rules."""
load("@rules_dotnet//dotnet:defs.bzl", "nuget_repo")

def _nuget_impl(ctx):
    packages = json.decode(ctx.read(Label("//:benchmarks/adapters/dotnet/packages.lock.json")))["dependencies"]["net10.0"]
    integrity = json.decode(ctx.read(Label("//:benchmarks/adapters/dotnet/nuget-integrity.json")))
    nuget_repo(
        name = "comparison_nuget",
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
    return ctx.extension_metadata(reproducible = True)

nuget = module_extension(implementation = _nuget_impl)
