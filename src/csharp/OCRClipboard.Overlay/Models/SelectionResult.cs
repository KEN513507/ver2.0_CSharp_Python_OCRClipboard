using System;

namespace OCRClipboard.Overlay.Models;

public sealed class SelectionResult
{
    public IntPtr MonitorHandle { get; init; }
    // Physical pixels, monitor-local origin (0,0) = monitor top-left
    public int X { get; init; }
    public int Y { get; init; }
    public int Width { get; init; }
    public int Height { get; init; }
}

