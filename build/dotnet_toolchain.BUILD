load("@rules_dotnet//dotnet:toolchain.bzl", "dotnet_toolchain")

package(default_visibility = ["//visibility:public"])

filegroup(
    name = "dotnet_muxer",
    srcs = ["dotnet/dotnet"],
    data = glob(["dotnet/host/**", "dotnet/shared/**"]),
)

filegroup(
    name = "csc",
    srcs = ["dotnet/sdk/{sdk}/Roslyn/bincore/csc.dll"],
    data = glob(["dotnet/sdk/{sdk}/Roslyn/bincore/**"]),
)

filegroup(
    name = "fsc",
    srcs = ["dotnet/sdk/{sdk}/FSharp/fsc.dll"],
    data = glob(["dotnet/sdk/{sdk}/FSharp/**"]),
)

dotnet_toolchain(
    name = "dotnet_toolchain",
    runtime = ":dotnet_muxer",
    csharp_compiler = ":csc",
    fsharp_compiler = ":fsc",
    sdk_version = "{sdk}",
    runtime_version = "{runtime}",
    runtime_tfm = "net10.0",
    csharp_default_version = "12.0",
    fsharp_default_version = "8.0",
)

toolchain(
    name = "dotnet_registered",
    toolchain = ":dotnet_toolchain",
    toolchain_type = "@rules_dotnet//dotnet:toolchain_type",
    exec_compatible_with = ["@platforms//os:{os}", "@platforms//cpu:{cpu}"],
    target_compatible_with = ["@platforms//os:{os}", "@platforms//cpu:{cpu}"],
)
