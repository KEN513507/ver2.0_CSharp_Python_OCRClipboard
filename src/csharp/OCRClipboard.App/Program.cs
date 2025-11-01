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

            // クロップ妥当性チェック（下端欠け防止）
            var width = bitmap.Width;
            var height = bitmap.Height;
            if (height < 40 || width / (double)height > 25.0)
            {
                Console.Error.WriteLine($"[WARN] Selection too thin (W={width} H={height}); OCR may fail. Consider reselecting.");
            }

            // 上下パディング追加（下端欠け対策）
            var pad = 8;
            var paddedBitmap = new Bitmap(width, height + 2 * pad);
            using (var g = System.Drawing.Graphics.FromImage(paddedBitmap))
            {
                g.Clear(System.Drawing.Color.White);
                g.DrawImage(bitmap, 0, pad);
            }

            OcrResult? ocrResult = null;
            try
            {
                ocrResult = await engine.RecognizeAsync(paddedBitmap);
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"[C#] OCR failed: {ex}");
                return;
            }
            finally
            {
                paddedBitmap.Dispose();
            }
            totalWatch.Stop();

            var timings = ocrResult.Timings;
            var captureMs = captureWatch.Elapsed.TotalMilliseconds;
            var convertMs = timings?.PreprocessMilliseconds ?? 0;
            var ocrMs = timings?.InferenceMilliseconds ?? 0;
            var totalMs = totalWatch.Elapsed.TotalMilliseconds;

            var sample = ocrResult.CombinedText.Length > 20 
                ? ocrResult.CombinedText[..20] + "…" 
                : ocrResult.CombinedText;

            // 固定フォーマット運用ログ（継続比較用）
            Console.WriteLine($"[PERF] capture={captureMs:F0}ms convert={convertMs:F0}ms ocr={ocrMs:F0}ms total={totalMs:F0}ms");
            Console.WriteLine($"[OCR] n_fragments={ocrResult.FragmentCount} mean_conf={ocrResult.MeanConfidence:F2} sample=\"{sample}\"");

            var combinedText = ocrResult.CombinedText;
            var clipboardCopied = false;
            if (!string.IsNullOrEmpty(combinedText))
            {
                TrySetClipboardText(combinedText);
                clipboardCopied = true;
            }
            Console.WriteLine($"[CLIPBOARD] copied={clipboardCopied.ToString().ToLower()} length={combinedText.Length}");
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
