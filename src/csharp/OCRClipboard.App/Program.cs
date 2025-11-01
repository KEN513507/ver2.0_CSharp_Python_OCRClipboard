using System.Diagnostics;
using System.Drawing;
using System.Threading;
using Ocr;

namespace OCRClipboard.App;

public partial class Program
{
    public static async Task Main(string[] args)
    {
        Console.WriteLine("[C#] Starting Windows.Media.Ocr engine...");

        var engine = new WindowsMediaOcrEngine();

        var totalWatch = Stopwatch.StartNew();
        var captureWatch = Stopwatch.StartNew();

        // Launch overlay selection window (single monitor, monitor-local physical coords)
        var selection = await OCRClipboard.Overlay.OverlayRunner.RunSelectionCaptureAsync();
        captureWatch.Stop();

        if (selection != null)
        {
            SaveDebugCapture(selection.Value.imageBase64);

            // Base64 → Bitmap
            var imageBytes = Convert.FromBase64String(selection.Value.imageBase64);
            using var ms = new System.IO.MemoryStream(imageBytes);
            using var bitmap = new Bitmap(ms);

            OcrResult? ocrResult = null;
            try
            {
                ocrResult = await engine.RecognizeAsync(bitmap);
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"[C#] OCR failed: {ex}");
                return;
            }
            totalWatch.Stop();

            var timings = ocrResult.Timings;
            var captureMs = captureWatch.Elapsed.TotalMilliseconds;
            var preprocMs = timings?.PreprocessMilliseconds ?? ocrResult.Elapsed.TotalMilliseconds;
            var inferMs = timings?.InferenceMilliseconds ?? 0;
            var postprocMs = timings?.PostprocessMilliseconds ?? 0;
            var totalMs = totalWatch.Elapsed.TotalMilliseconds;

            // [PERF] ログ出力
            Console.WriteLine(
                "[PERF] capture={0:F0}ms preproc={1:F0}ms infer={2:F0}ms postproc={3:F0}ms total={4:F0}ms",
                captureMs,
                preprocMs,
                inferMs,
                postprocMs,
                totalMs);
            Console.WriteLine(
                "[OCR] n_fragments={0} mean_conf={1:F2} min_conf={2:F2}",
                ocrResult.FragmentCount,
                ocrResult.MeanConfidence,
                ocrResult.MinConfidence);

            var combinedText = ocrResult.CombinedText;
            Console.WriteLine($"[C#] OCR Text: '{combinedText}'");
            if (!string.IsNullOrEmpty(combinedText))
            {
                TrySetClipboardText(combinedText);
                var preview = combinedText.Length <= 40
                    ? combinedText
                    : combinedText[..40];
                Console.WriteLine($"[CLIPBOARD] {preview}");
            }
        }

        totalWatch.Stop();
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
