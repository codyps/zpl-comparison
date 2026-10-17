// swift-tools-version: 6.4
import PackageDescription

let package = Package(
    name: "ZPLKitComparison",
    platforms: [.macOS(.v27)],
    dependencies: [.package(path: "../../_work/zplkit")],
    targets: [
        .executableTarget(
            name: "zplkit-adapter",
            dependencies: [.product(name: "ZPLKitRenderer", package: "zplkit")]
        )
    ]
)
