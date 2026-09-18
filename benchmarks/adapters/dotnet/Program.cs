// API: https://github.com/BinaryKits/BinaryKits.Zpl#how-can-i-use-it
using System.Diagnostics;
using System.Text.Json;
using BinaryKits.Zpl.Viewer;

var mode = args[0];
var source = File.ReadAllText(args[1]);
var n = int.Parse(args[2]);
var width = args.Length > 4 ? int.Parse(args[4]) : 400;
var height = args.Length > 5 ? int.Parse(args[5]) : 300;
if (n < 1) throw new ArgumentException("iterations");
byte[] Operation() {
    var storage = new PrinterStorage();
    var info = new ZplAnalyzer(storage).Analyze(source);
    if (info.LabelInfos.Length != 1) throw new Exception("Expected one label");
    if (mode == "parse") { GC.KeepAlive(info); return new byte[] {1}; }
    return new ZplElementDrawer(storage).Draw(info.LabelInfos[0].ZplElements, width / 8.0, height / 8.0, 8);
}
if (mode == "accuracy") { File.WriteAllBytes(args[3], Operation()); return; }
var warmup = Stopwatch.StartNew();
for (var i=0; i<3 || warmup.ElapsedMilliseconds < 250; i++) GC.KeepAlive(Operation());
var start = Stopwatch.GetTimestamp();
long checksum = 0;
for (var i=0; i<n; i++) { var result=Operation(); checksum+=result.Length; GC.KeepAlive(result); }
var ns = Stopwatch.GetElapsedTime(start).TotalNanoseconds;
File.WriteAllBytes(args[3], Operation());
Console.WriteLine(JsonSerializer.Serialize(new { ns, iterations=n, checksum }));
