// API: https://www.neodynamic.com/Products/Help/ZPLPrinterEmulatorSDK8.0/api/Neodynamic.SDK.ZPLPrinter.ZPLPrinter.html
using System;
using System.IO;
using System.Collections.Generic;
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using Neodynamic.SDK.ZPLPrinter;

Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);

void Run(string[] args) {
    if (args.Length < 4) throw new ArgumentException("mode input iterations output [width height]");
    var mode = args[0];
    if (mode != "png" && mode != "accuracy" && mode != "probe-render")
        throw new ArgumentException("Unsupported mode: " + mode);
    // Use the byte API so binary graphics and ^CI encoding commands reach the SDK intact.
    var source = File.ReadAllBytes(args[1]);
    var n = int.Parse(args[2]);
    var width = args.Length > 4 ? int.Parse(args[4]) : 400;
    var height = args.Length > 5 ? int.Parse(args[5]) : 300;
    if (n < 1 || width < 1 || height < 1) throw new ArgumentException("Positive iterations and canvas required");

    List<byte[]> Operation() {
        // A virtual printer retains downloads and command state: isolate every document.
        // Empty credentials deliberately select evaluation mode, including its unmodified stamp.
        using var printer = new ZPLPrinter("", "") {
            Dpi = 203,
            LabelWidth = width,
            LabelHeight = height,
            RenderOutputFormat = RenderOutputFormat.PNG,
        };
        return printer.ProcessCommands(source);
    }
    byte[] SingleLabel() {
        var labels = Operation();
        if (labels == null || labels.Count != 1) throw new Exception("Expected one label");
        return labels[0];
    }
    if (mode == "probe-render") {
        List<byte[]>? labels;
        try { labels = Operation(); }
        catch (Exception error) {
            Console.Error.WriteLine(error);
            Console.WriteLine("rejected");
            return;
        }
        if (labels == null || labels.Count == 0) Console.WriteLine("accepted-empty");
        else {
            File.WriteAllBytes(args[3], labels[0]);
            Console.WriteLine("accepted");
        }
        return;
    }
    if (mode == "accuracy") { File.WriteAllBytes(args[3], SingleLabel()); return; }
    var warmup = Stopwatch.StartNew();
    for (var i = 0; i < 3 || (Environment.GetEnvironmentVariable("ZPL_BENCH_MEMORY") != "1" && warmup.ElapsedMilliseconds < 250); i++)
        GC.KeepAlive(SingleLabel());
    var start = Stopwatch.GetTimestamp();
    long checksum = 0;
    for (var i = 0; i < n; i++) {
        var result = SingleLabel();
        checksum += result.Length;
        GC.KeepAlive(result);
    }
    var ns = Stopwatch.GetElapsedTime(start).TotalNanoseconds;
    File.WriteAllBytes(args[3], SingleLabel());
    Console.WriteLine(JsonSerializer.Serialize(new { ns, iterations = n, checksum }));
}

if (args.Length == 1 && args[0] == "--session") {
    var protocol = Console.Out;
    var errors = Console.Error;
    var directory = Environment.CurrentDirectory;
    string? line;
    while ((line = Console.ReadLine()) != null) {
        var request = JsonSerializer.Deserialize<RenderRequest>(line)!;
        using var diagnostic = new TailWriter();
        var exitCode = 0;
        Console.SetOut(TextWriter.Null);
        Console.SetError(diagnostic);
        try {
            Environment.CurrentDirectory = request.cwd;
            foreach (var entry in request.env) Environment.SetEnvironmentVariable(entry.Key, entry.Value);
            Run(request.args);
        } catch (Exception error) {
            exitCode = 1;
            diagnostic.Write(error.ToString());
        } finally {
            Console.SetOut(protocol);
            Console.SetError(errors);
            Environment.CurrentDirectory = directory;
        }
        protocol.WriteLine(JsonSerializer.Serialize(new { request.id, exitCode, diagnostic = diagnostic.ToString() }));
        protocol.Flush();
    }
} else {
    try { Run(args); }
    catch (Exception error) {
        Console.Error.WriteLine(error);
        Environment.ExitCode = 1;
    }
}

record RenderRequest(int id, string[] args, string cwd, Dictionary<string, string> env);

sealed class TailWriter : StringWriter {
    public override void Write(char value) { base.Write(value); Trim(); }
    public override void Write(string? value) { base.Write(value); Trim(); }
    public override void WriteLine(string? value) { Write(value); Write(NewLine); }
    private void Trim() {
        var buffer = GetStringBuilder();
        if (buffer.Length > 1800) buffer.Remove(0, buffer.Length - 1800);
    }
}
