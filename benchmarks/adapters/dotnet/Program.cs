// API: https://github.com/BinaryKits/BinaryKits.Zpl#how-can-i-use-it
using System.Diagnostics;
using System.Text.Json;
using BinaryKits.Zpl.Viewer;
using BinaryKits.Zpl.Viewer.ElementDrawers;
using SkiaSharp;

var mode = args[0];
// The analyzer accepts Unicode text; never replace unrepresentable input bytes.
var source = new System.Text.UTF8Encoding(false, true).GetString(File.ReadAllBytes(args[1]));
var n = int.Parse(args[2]);
var width = args.Length > 4 ? int.Parse(args[4]) : 400;
var height = args.Length > 5 ? int.Parse(args[5]) : 300;
if (n < 1) throw new ArgumentException("iterations");
// Match the upstream WebApi font mapping without relying on host font discovery.
// Assets and their licenses are pinned alongside this adapter.
var fontDirectory = Path.Combine(AppContext.BaseDirectory, "fonts");
using var proportional = SKTypeface.FromFile(Path.Combine(fontDirectory, "TeX Gyre Heros Cn-Bold.otf"))
    ?? throw new Exception("Missing bundled proportional font");
using var mono = SKTypeface.FromFile(Path.Combine(fontDirectory, "DejaVu Sans Mono.ttf"))
    ?? throw new Exception("Missing bundled monospace font");
ZplElementDrawer Drawer(IPrinterStorage storage) => new(storage, new DrawerOptions(new FontManager {
    FontLoader = name => name == "0" ? proportional : mono,
}));
byte[] Operation() {
    var storage = new PrinterStorage();
    var info = new ZplAnalyzer(storage).Analyze(source);
    if (info.LabelInfos.Length != 1) throw new Exception("Expected one label");
    if (mode == "parse") { GC.KeepAlive(info); return new byte[] {1}; }
    return Drawer(storage).Draw(info.LabelInfos[0].ZplElements, width / 8.0, height / 8.0, 8);
}
if (mode == "probe-parse" || mode == "probe-render") {
    byte[]? output = null;
    var verdict = "accepted";
    try {
        var storage = new PrinterStorage();
        var info = new ZplAnalyzer(storage).Analyze(source);
        if (info.Errors.Length > 0) {
            foreach (var error in info.Errors) Console.Error.WriteLine(error);
            verdict = "rejected";
        } else if (mode == "probe-render") {
            if (info.LabelInfos.Length == 0) verdict = "accepted-empty";
            else output = Drawer(storage).Draw(info.LabelInfos[0].ZplElements, width / 8.0, height / 8.0, 8);
        }
    } catch (Exception error) {
        Console.Error.WriteLine(error);
        verdict = "rejected";
    }
    if (output != null) File.WriteAllBytes(args[3], output);
    Console.WriteLine(verdict);
    return;
}
if (mode == "accuracy") { File.WriteAllBytes(args[3], Operation()); return; }
var warmup = Stopwatch.StartNew();
for (var i=0; i<3 || (Environment.GetEnvironmentVariable("ZPL_BENCH_MEMORY") != "1" && warmup.ElapsedMilliseconds < 250); i++) GC.KeepAlive(Operation());
var start = Stopwatch.GetTimestamp();
long checksum = 0;
for (var i=0; i<n; i++) { var result=Operation(); checksum+=result.Length; GC.KeepAlive(result); }
var ns = Stopwatch.GetElapsedTime(start).TotalNanoseconds;
File.WriteAllBytes(args[3], Operation());
Console.WriteLine(JsonSerializer.Serialize(new { ns, iterations=n, checksum }));
