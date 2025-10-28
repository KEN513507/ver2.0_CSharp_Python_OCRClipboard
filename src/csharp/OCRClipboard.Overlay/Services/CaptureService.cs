using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media.Imaging;
using OCRClipboard.Overlay.Native;

namespace OCRClipboard.Overlay.Services;

public static class CaptureService
{
    // One-shot capture fallback: GDI BitBlt (not protected content, not secure desktop)
    public static byte[] CaptureToPng(IntPtr hMonitor, int x, int y, int width, int height)
    {
        var mi = new Win32.MONITORINFO();
        if (!Win32.GetMonitorInfo(hMonitor, mi)) throw new InvalidOperationException("GetMonitorInfo failed");

        // Monitor rect in virtual screen coordinates
        var monLeft = mi.rcMonitor.Left;
        var monTop = mi.rcMonitor.Top;

        // Translate monitor-local physical coords (x,y) to virtual-screen origin
        var srcX = monLeft + x;
        var srcY = monTop + y;

        CaptureDiagnostics.RecordCaptureInvocation(new CaptureInvocationDiagnostics
        {
            MonitorHandle = CaptureDiagnostics.FormatHandle(hMonitor),
            MonitorRect = new RectInt(
                mi.rcMonitor.Left,
                mi.rcMonitor.Top,
                mi.rcMonitor.Right - mi.rcMonitor.Left,
                mi.rcMonitor.Bottom - mi.rcMonitor.Top),
            RequestedMonitorLocalPixels = new RectInt(x, y, width, height),
            RequestedVirtualScreenPixels = new RectInt(srcX, srcY, width, height)
        });

        var hDesktop = IntPtr.Zero;
        var hdcScreen = Win32.GetDC(hDesktop);
        var hdcMem = Win32.CreateCompatibleDC(hdcScreen);
        var hBmp = Win32.CreateCompatibleBitmap(hdcScreen, width, height);
        var hOld = Win32.SelectObject(hdcMem, hBmp);

        if (!Win32.BitBlt(hdcMem, 0, 0, width, height, hdcScreen, srcX, srcY, Win32.SRCCOPY))
        {
            var error = Marshal.GetLastWin32Error();
            throw new InvalidOperationException($"BitBlt failed (0x{error:X})");
        }

        var bmpSource = Imaging.CreateBitmapSourceFromHBitmap(
            hBmp,
            IntPtr.Zero,
            Int32Rect.Empty,
            BitmapSizeOptions.FromEmptyOptions());

        Win32.SelectObject(hdcMem, hOld);
        Win32.DeleteObject(hBmp);
        Win32.DeleteDC(hdcMem);
        Win32.ReleaseDC(hDesktop, hdcScreen);

        using var ms = new MemoryStream();
        var encoder = new PngBitmapEncoder();
        encoder.Frames.Add(BitmapFrame.Create(bmpSource));
        encoder.Save(ms);

        // 保存先: repo直下/logs/debug_capture.png
        var repoRoot = TryFindRepoRoot(AppContext.BaseDirectory) ?? Environment.CurrentDirectory;
        var logsDir = Path.Combine(repoRoot, "logs");
        Directory.CreateDirectory(logsDir);
        var savePath = Path.Combine(logsDir, "debug_capture.png");
        File.WriteAllBytes(savePath, ms.ToArray());

        return ms.ToArray();

        // .gitを辿ってrepo rootを判定
        static string? TryFindRepoRoot(string startDir)
        {
            var dir = new DirectoryInfo(startDir);
            while (dir != null && !File.Exists(Path.Combine(dir.FullName, ".git")))
                dir = dir.Parent;
            return dir?.FullName;
        }
    }
}
