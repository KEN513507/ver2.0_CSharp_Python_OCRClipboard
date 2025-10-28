using System;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Controls;
using OCRClipboard.Overlay.Models;
using OCRClipboard.Overlay.Native;
using OCRClipboard.Overlay.Services;

namespace OCRClipboard.Overlay;

public partial class OverlayWindow : Window
{
    private IntPtr _hMonitor;
    private Win32.MONITORINFO _mi = new();
    private Point? _startPt;
    private Rect _selection;
    private double _dpiScaleX = 1.0;
    private double _dpiScaleY = 1.0;

    public SelectionResult? Result { get; private set; }

    public OverlayWindow()
    {
        InitializeComponent();
        SourceInitialized += OnSourceInitialized;
    }

    private void OnSourceInitialized(object? sender, EventArgs e)
    {
        var hwndSource = PresentationSource.FromVisual(this) as HwndSource;
        if (hwndSource == null) return;
        var hwnd = hwndSource.Handle;

        SetWindowStyles(hwnd);

        if (!Win32.GetCursorPos(out var pt)) { Close(); return; }
        _hMonitor = Win32.MonitorFromPoint(pt, Win32.MONITOR_DEFAULTTONEAREST);
        _mi = new Win32.MONITORINFO();
        if (!Win32.GetMonitorInfo(_hMonitor, _mi)) { Close(); return; }

        var dpi = VisualTreeHelper.GetDpi(this);
        _dpiScaleX = dpi.DpiScaleX;
        _dpiScaleY = dpi.DpiScaleY;

        Left = _mi.rcMonitor.Left / _dpiScaleX;
        Top = _mi.rcMonitor.Top / _dpiScaleY;
        Width = (_mi.rcMonitor.Right - _mi.rcMonitor.Left) / _dpiScaleX;
        Height = (_mi.rcMonitor.Bottom - _mi.rcMonitor.Top) / _dpiScaleY;

        LogMonitorAndWindowState();
    }

    private static void SetWindowStyles(IntPtr hwnd)
    {
        var ex = Win32.GetWindowLongPtr(hwnd, Win32.GWL_EXSTYLE);
        var newEx = new IntPtr(ex.ToInt64() | Win32.WS_EX_LAYERED | Win32.WS_EX_TOOLWINDOW | Win32.WS_EX_TOPMOST);
        Win32.SetWindowLongPtr(hwnd, Win32.GWL_EXSTYLE, newEx);
    }

    private void OnKeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Escape)
        {
            Result = null;
            Close();
        }
        else if (e.Key == Key.Enter)
        {
            ConfirmSelectionAndClose();
        }
    }

    private void OnMouseDown(object sender, MouseButtonEventArgs e)
    {
        CaptureMouse();
        _startPt = e.GetPosition(this);
        _selection = new Rect(_startPt.Value, _startPt.Value);
        SelectionRect.Visibility = Visibility.Visible;
        UpdateSelectionRect();
    }

    private void OnMouseMove(object sender, MouseEventArgs e)
    {
        if (_startPt is null) return;
        var current = e.GetPosition(this);
        _selection = new Rect(_startPt.Value, current);
        UpdateSelectionRect();
    }

    private void OnMouseUp(object sender, MouseButtonEventArgs e)
    {
        if (_startPt is null) return;
        ReleaseMouseCapture();
        ConfirmSelectionAndClose();
    }

    private void UpdateSelectionRect()
    {
        var r = _selection;
        if (r.Width < 0) { r = new Rect(r.X + r.Width, r.Y, -r.Width, r.Height); }
        if (r.Height < 0) { r = new Rect(r.X, r.Y + r.Height, r.Width, -r.Height); }
        Canvas.SetLeft(SelectionRect, r.X);
        Canvas.SetTop(SelectionRect, r.Y);
        SelectionRect.Width = r.Width;
        SelectionRect.Height = r.Height;
    }

    private void ConfirmSelectionAndClose()
    {
        var r = _selection;
        if (r.Width < 0) { r = new Rect(r.X + r.Width, r.Y, -r.Width, r.Height); }
        if (r.Height < 0) { r = new Rect(r.X, r.Y + r.Height, r.Width, -r.Height); }

        LogSelection(r);

        // Convert from WPF DIPs to physical pixels, monitor-local origin
        var screenLeftDip = Left + r.X;
        var screenTopDip = Top + r.Y;

        var virtualLeftExact = screenLeftDip * _dpiScaleX;
        var virtualTopExact = screenTopDip * _dpiScaleY;
        var virtualWidthExact = r.Width * _dpiScaleX;
        var virtualHeightExact = r.Height * _dpiScaleY;

        var leftPxVirtual = (int)Math.Round(virtualLeftExact);
        var topPxVirtual = (int)Math.Round(virtualTopExact);
        var px = leftPxVirtual - _mi.rcMonitor.Left;
        var py = topPxVirtual - _mi.rcMonitor.Top;
        var widthPx = Math.Max((int)Math.Round(virtualWidthExact), 1);
        var heightPx = Math.Max((int)Math.Round(virtualHeightExact), 1);

        Result = new SelectionResult
        {
            MonitorHandle = _hMonitor,
            X = Math.Max(px, 0),
            Y = Math.Max(py, 0),
            Width = widthPx,
            Height = heightPx
        };

        CaptureDiagnostics.RecordSelection(new SelectionDiagnostics
        {
            MonitorHandle = CaptureDiagnostics.FormatHandle(_hMonitor),
            MonitorRect = new RectInt(
                _mi.rcMonitor.Left,
                _mi.rcMonitor.Top,
                _mi.rcMonitor.Right - _mi.rcMonitor.Left,
                _mi.rcMonitor.Bottom - _mi.rcMonitor.Top),
            WorkAreaRect = new RectInt(
                _mi.rcWork.Left,
                _mi.rcWork.Top,
                _mi.rcWork.Right - _mi.rcWork.Left,
                _mi.rcWork.Bottom - _mi.rcWork.Top),
            DpiScaleX = _dpiScaleX,
            DpiScaleY = _dpiScaleY,
            WindowRectDips = new RectDouble(Left, Top, Width, Height),
            SelectionLogicalDips = new RectDouble(r.X, r.Y, r.Width, r.Height),
            SelectionVirtualScreenExact = new RectDouble(virtualLeftExact, virtualTopExact, virtualWidthExact, virtualHeightExact),
            SelectionVirtualScreenPixels = new RectInt(leftPxVirtual, topPxVirtual, widthPx, heightPx),
            SelectionMonitorLocalPixels = new RectInt(px, py, widthPx, heightPx),
            ResultRect = new RectInt(Result.X, Result.Y, Result.Width, Result.Height)
        });

        Close();
    }

    private void LogMonitorAndWindowState()
    {
        Console.WriteLine("[COORD] === Monitor & Window Coordinates ===");
        Console.WriteLine($"[COORD] rcMonitor (physical px): Left={_mi.rcMonitor.Left}, Top={_mi.rcMonitor.Top}, Right={_mi.rcMonitor.Right}, Bottom={_mi.rcMonitor.Bottom}");
        Console.WriteLine($"[COORD] Monitor size (physical): {_mi.rcMonitor.Right - _mi.rcMonitor.Left} x {_mi.rcMonitor.Bottom - _mi.rcMonitor.Top}");
        Console.WriteLine($"[COORD] DPI Scale: X={_dpiScaleX:F4}, Y={_dpiScaleY:F4}");

        var expectedLeftDip = _mi.rcMonitor.Left / _dpiScaleX;
        var expectedTopDip = _mi.rcMonitor.Top / _dpiScaleY;
        var expectedWidthDip = (_mi.rcMonitor.Right - _mi.rcMonitor.Left) / _dpiScaleX;
        var expectedHeightDip = (_mi.rcMonitor.Bottom - _mi.rcMonitor.Top) / _dpiScaleY;

        Console.WriteLine($"[COORD] WPF Window.Left/Top/Width/Height (DIPs): Left={Left:F2}, Top={Top:F2}, Width={Width:F2}, Height={Height:F2}");
        Console.WriteLine($"[COORD] Expected DIPs: Left={expectedLeftDip:F2}, Top={expectedTopDip:F2}, Width={expectedWidthDip:F2}, Height={expectedHeightDip:F2}");
        Console.WriteLine($"[COORD] Mismatch: Left={Math.Abs(Left - expectedLeftDip):F2}, Top={Math.Abs(Top - expectedTopDip):F2}, Width={Math.Abs(Width - expectedWidthDip):F2}, Height={Math.Abs(Height - expectedHeightDip):F2}");
    }

    private void LogSelection(Rect selectionDip)
    {
        Console.WriteLine("[SELECT] === User Selection ===");
        Console.WriteLine($"[SELECT] Logical rect (DIPs): X={selectionDip.X:F2}, Y={selectionDip.Y:F2}, W={selectionDip.Width:F2}, H={selectionDip.Height:F2}");
        Console.WriteLine($"[SELECT] Window offset (DIPs as stored): Left={Left:F2}, Top={Top:F2}");
        Console.WriteLine($"[SELECT] DPI scale: X={_dpiScaleX:F4}, Y={_dpiScaleY:F4}");

        var screenLeftDip = Left + selectionDip.X;
        var screenTopDip = Top + selectionDip.Y;
        var leftPxVirtual = (int)Math.Round(screenLeftDip * _dpiScaleX);
        var topPxVirtual = (int)Math.Round(screenTopDip * _dpiScaleY);
        var expectedLeftPx = _mi.rcMonitor.Left + (int)Math.Round(selectionDip.X * _dpiScaleX);
        var expectedTopPx = _mi.rcMonitor.Top + (int)Math.Round(selectionDip.Y * _dpiScaleY);

        Console.WriteLine($"[SELECT] Converted physical (current logic): X={leftPxVirtual}, Y={topPxVirtual}, W={(int)Math.Round(selectionDip.Width * _dpiScaleX)}, H={(int)Math.Round(selectionDip.Height * _dpiScaleY)}");
        Console.WriteLine($"[SELECT] Expected physical (monitor origin + selection): X={expectedLeftPx}, Y={expectedTopPx}");
        Console.WriteLine($"[SELECT] Difference vs expected: dX={Math.Abs(leftPxVirtual - expectedLeftPx)}, dY={Math.Abs(topPxVirtual - expectedTopPx)}");
        Console.WriteLine($"[SELECT] Result offsets (monitor-local): X={leftPxVirtual - _mi.rcMonitor.Left}, Y={topPxVirtual - _mi.rcMonitor.Top}");
    }

}
