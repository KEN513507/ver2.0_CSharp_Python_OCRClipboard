using System;
using System.Threading;
using System.Threading.Tasks;

namespace OCRClipboard.Overlay;

public static class OverlayRunner
{
    public static Task<(string imageBase64, int width, int height)?> RunSelectionCaptureAsync()
    {
        var tcs = new TaskCompletionSource<(string, int, int)?>();
        var th = new Thread(() =>
        {
            try
            {
                var app = new System.Windows.Application();
                var win = new OverlayWindow();
                win.ShowDialog();
                var result = win.Result;
                if (result == null)
                {
                    tcs.TrySetResult(null);
                }
                else
                {
                    var png = Services.CaptureService.CaptureToPng(
                        result.MonitorHandle, result.X, result.Y, result.Width, result.Height);
                    var b64 = Convert.ToBase64String(png);
                    tcs.TrySetResult((b64, result.Width, result.Height));
                }
            }
            catch (Exception ex)
            {
                tcs.TrySetException(ex);
            }
            finally
            {
                System.Windows.Application.Current?.Shutdown();
            }
        });
        th.SetApartmentState(ApartmentState.STA);
        th.IsBackground = true;
        th.Start();
        return tcs.Task;
    }
}

