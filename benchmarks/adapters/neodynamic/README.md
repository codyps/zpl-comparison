# Neodynamic adapter

See [methodology and trial limitations](../../README.md#neodynamic-c--net).
This standalone C# application implements `accuracy`, `png`, `probe-render` and
`--session` with the shared adapter protocol. Its NuGet lock is independent of
BinaryKits so the older compatible SkiaSharp API remains isolated.

```sh
dotnet restore Comparison.csproj --locked-mode
dotnet publish Comparison.csproj --no-restore -c Release -o ../../_work/neodynamic-out
dotnet ../../_work/neodynamic-out/Comparison.dll accuracy ../../fixtures/text.zpl 1 sample.png 400 300
```

Use only for comparison/testing under the package's commercial evaluation terms.
All output retains the SDK trial stamp and resident-font substitutions. The stamp
color varies per render; PNG hashes and fidelity scores can therefore vary. No
commercial license credentials or vendor binaries are stored in this repository.
