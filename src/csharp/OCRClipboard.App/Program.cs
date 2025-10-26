using System.Text.Json;
using System.Text.Json.Serialization;
using OCRClipboard.App.Ipc;
using OCRClipboard.App.Dto;

namespace OCRClipboard.App;

public partial class Program
{
    public static async Task Main(string[] args)
    {
        Console.WriteLine("[C#] Starting Python worker and launching overlay...");

        using var host = new PythonProcessHost(
            pythonExe: "python",
            module: "ocr_worker.main",
            workingDirectory: Directory.GetCurrentDirectory());

        await host.StartAsync();

        var client = new JsonRpcClient(host);

        // Health check
        var health = await client.CallAsync<HealthOk>(
            type: "health.check",
            payload: new HealthCheck { Reason = "startup" },
            CancellationToken.None);
        Console.WriteLine($"[C#] Health OK: {health?.Message}");

        // Launch overlay selection window (single monitor, monitor-local physical coords)
        var selection = await OCRClipboard.Overlay.OverlayRunner.RunSelectionCaptureAsync();
        if (selection != null)
        {
            SaveDebugCapture(selection.Value.imageBase64);

            var req = new OcrRequest
            {
                Language = "eng",
                Source = "imageBase64",
                ImageBase64 = selection.Value.imageBase64
            };
            var ocr = await client.CallAsync<OcrResponse>(
                type: "ocr.perform",
                payload: req,
                CancellationToken.None);
            Console.WriteLine($"[C#] OCR Text: '{ocr?.Text}' (conf={ocr?.Confidence})");
            if (!string.IsNullOrEmpty(ocr?.Text))
            {
                TrySetClipboardText(ocr!.Text);
            }
        }

        await host.StopAsync();
        Console.WriteLine("[C#] Done.");
    }
}

public partial class Program
{
    private static void TrySetClipboardText(string text)
    {
        var done = new ManualResetEvent(false);
        var th = new Thread(() =>
        {
            try
            {
                System.Windows.Forms.Clipboard.SetText(text);
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"[C#] Clipboard set failed: {ex.Message}");
            }
            finally
            {
                done.Set();
            }
        });
        th.SetApartmentState(ApartmentState.STA);
        th.Start();
        done.WaitOne(TimeSpan.FromSeconds(2));
    }

    private static void SaveDebugCapture(string base64)
    {
        try
        {
            var path = Path.Combine(Environment.CurrentDirectory, "debug_capture.png");
            var bytes = Convert.FromBase64String(base64);
            File.WriteAllBytes(path, bytes);

            if (File.Exists(path))
            {
                Console.WriteLine($"[C#] Debug capture saved: {path}");
            }
            else
            {
                Console.Error.WriteLine("[C#] Debug capture save attempted, but file not found afterwards.");
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"[C#] Failed to save debug capture: {ex.Message}");
        }
    }
    
}
