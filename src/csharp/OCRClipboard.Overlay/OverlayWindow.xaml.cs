using System;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using OCRClipboard.Overlay.Models;
using OCRClipboard.Overlay.Native;

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
        Loaded += OnLoaded;
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        var hwnd = new WindowInteropHelper(this).Handle;
        SetWindowStyles(hwnd);

        // Pick monitor under cursor
        if (!Win32.GetCursorPos(out var pt)) Close();
        _hMonitor = Win32.MonitorFromPoint(pt, Win32.MONITOR_DEFAULTTONEAREST);
        _mi = new Win32.MONITORINFO();
        if (!Win32.GetMonitorInfo(_hMonitor, _mi)) Close();

        // Position to exactly cover target monitor (virtual-screen coords)
        Left = _mi.rcMonitor.Left;
        Top = _mi.rcMonitor.Top;
        Width = _mi.rcMonitor.Right - _mi.rcMonitor.Left;
        Height = _mi.rcMonitor.Bottom - _mi.rcMonitor.Top;

        var dpi = VisualTreeHelper.GetDpi(this);
        _dpiScaleX = dpi.DpiScaleX;
        _dpiScaleY = dpi.DpiScaleY;
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

        // Convert from WPF DIPs to physical pixels, monitor-local origin
        var px = (int)Math.Round(r.X * _dpiScaleX);
        var py = (int)Math.Round(r.Y * _dpiScaleY);
        var pw = (int)Math.Round(r.Width * _dpiScaleX);
        var ph = (int)Math.Round(r.Height * _dpiScaleY);

        Result = new SelectionResult
        {
            MonitorHandle = _hMonitor,
            X = Math.Max(px, 0),
            Y = Math.Max(py, 0),
            Width = Math.Max(pw, 1),
            Height = Math.Max(ph, 1)
        };

        Close();
    }
}

