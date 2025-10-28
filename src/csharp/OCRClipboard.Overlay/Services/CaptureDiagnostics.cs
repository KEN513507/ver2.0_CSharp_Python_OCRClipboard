using System;
using System.IO;
using System.Text;
using System.Text.Json;

namespace OCRClipboard.Overlay.Services;

internal static class CaptureDiagnostics
{
    private static readonly object Gate = new();
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = false
    };
    private static readonly Encoding Utf8NoBom = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false);

    public static string? CurrentScenario =>
        Environment.GetEnvironmentVariable("OCR_COORD_SCENARIO");

    public static void RecordSelection(SelectionDiagnostics selection)
    {
        var entry = new CaptureDiagnosticsEntry
        {
            Timestamp = DateTimeOffset.UtcNow,
            Scenario = CurrentScenario,
            Event = "selection",
            Selection = selection
        };
        Append(entry);
    }

    public static void RecordCaptureInvocation(CaptureInvocationDiagnostics capture)
    {
        var entry = new CaptureDiagnosticsEntry
        {
            Timestamp = DateTimeOffset.UtcNow,
            Scenario = CurrentScenario,
            Event = "capture",
            Capture = capture
        };
        Append(entry);
    }

    public static string FormatHandle(IntPtr handle) => $"0x{handle.ToInt64():X}";

    private static void Append(CaptureDiagnosticsEntry entry)
    {
        var logPath = GetLogPath();
        var payload = JsonSerializer.Serialize(entry, JsonOptions) + Environment.NewLine;
        lock (Gate)
        {
            using var stream = new FileStream(logPath, FileMode.OpenOrCreate, FileAccess.Write, FileShare.ReadWrite);
            stream.Seek(0, SeekOrigin.End);
            using var writer = new StreamWriter(stream, Utf8NoBom, leaveOpen: false);
            writer.Write(payload);
        }
    }

    private static string GetLogPath()
    {
        var repoRoot = TryFindRepoRoot(AppContext.BaseDirectory) ?? Environment.CurrentDirectory;
        var logsDir = Path.Combine(repoRoot, "logs");
        Directory.CreateDirectory(logsDir);
        var stamp = DateTime.UtcNow.ToString("yyyyMMdd");
        return Path.Combine(logsDir, $"capture_diagnostics_{stamp}.jsonl");
    }

    private static string? TryFindRepoRoot(string startDir)
    {
        var dir = new DirectoryInfo(startDir);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, ".git")))
        {
            dir = dir.Parent;
        }
        return dir?.FullName;
    }
}

internal sealed record CaptureDiagnosticsEntry
{
    public DateTimeOffset Timestamp { get; init; }
    public string? Scenario { get; init; }
    public string Event { get; init; } = string.Empty;
    public SelectionDiagnostics? Selection { get; init; }
    public CaptureInvocationDiagnostics? Capture { get; init; }
}

internal sealed record SelectionDiagnostics
{
    public string MonitorHandle { get; init; } = string.Empty;
    public RectInt MonitorRect { get; init; }
    public RectInt WorkAreaRect { get; init; }
    public double DpiScaleX { get; init; }
    public double DpiScaleY { get; init; }
    public RectDouble WindowRectDips { get; init; }
    public RectDouble SelectionLogicalDips { get; init; }
    public RectDouble SelectionVirtualScreenExact { get; init; }
    public RectInt SelectionVirtualScreenPixels { get; init; }
    public RectInt SelectionMonitorLocalPixels { get; init; }
    public RectInt ResultRect { get; init; }
}

internal sealed record CaptureInvocationDiagnostics
{
    public string MonitorHandle { get; init; } = string.Empty;
    public RectInt MonitorRect { get; init; }
    public RectInt RequestedMonitorLocalPixels { get; init; }
    public RectInt RequestedVirtualScreenPixels { get; init; }
}

internal readonly record struct RectDouble(double X, double Y, double Width, double Height);

internal readonly record struct RectInt(int Left, int Top, int Width, int Height)
{
    public int Right => Left + Width;
    public int Bottom => Top + Height;
}
