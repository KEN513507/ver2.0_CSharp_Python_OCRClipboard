using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;
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

        var hDesktop = IntPtr.Zero;
        var hdcScreen = Win32.GetDC(hDesktop);
        var hdcMem = Win32.CreateCompatibleDC(hdcScreen);
        var hBmp = Win32.CreateCompatibleBitmap(hdcScreen, width, height);
        var hOld = Win32.SelectObject(hdcMem, hBmp);

        Win32.BitBlt(hdcMem, 0, 0, width, height, hdcScreen, srcX, srcY, Win32.SRCCOPY);

        using var bmp = Image.FromHbitmap(hBmp);
        Win32.SelectObject(hdcMem, hOld);
        Win32.DeleteObject(hBmp);
        Win32.DeleteDC(hdcMem);
        Win32.ReleaseDC(hDesktop, hdcScreen);

        using var ms = new MemoryStream();
        bmp.Save(ms, ImageFormat.Png);
        return ms.ToArray();
    }
}

