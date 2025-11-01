using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices.WindowsRuntime;
using System.Threading;
using System.Threading.Tasks;
using Windows.Graphics.Imaging;
using Windows.Media.Ocr;
using Windows.Storage.Streams;

namespace Ocr;

/// <summary>
/// Windows.Media.Ocr をラップするクラス（日本語・英語対応）
/// </summary>
public sealed class WindowsMediaOcrEngine : IOcrEngine
{
    private readonly OcrEngine _engine;

    public WindowsMediaOcrEngine()
    {
        // 日本語を優先、フォールバックで英語
        var jpLang = new Windows.Globalization.Language("ja");
        if (OcrEngine.IsLanguageSupported(jpLang))
        {
            _engine = OcrEngine.TryCreateFromLanguage(jpLang);
        }
        else
        {
            // 日本語が使えない場合は英語
            var enLang = new Windows.Globalization.Language("en");
            _engine = OcrEngine.TryCreateFromLanguage(enLang);
        }

        if (_engine == null)
        {
            throw new InvalidOperationException("Windows.Media.Ocr がサポートされていません。");
        }
    }

    public async Task<OcrResult> RecognizeAsync(Bitmap bitmap, CancellationToken ct = default)
    {
        if (bitmap is null) throw new ArgumentNullException(nameof(bitmap));
        ct.ThrowIfCancellationRequested();

        var totalWatch = Stopwatch.StartNew();

        var preprocessWatch = Stopwatch.StartNew();
        using var stream = new InMemoryRandomAccessStream();
        using (var memory = new MemoryStream())
        {
            // PNG形式で保存（WICコーデック互換性のため）
            bitmap.Save(memory, System.Drawing.Imaging.ImageFormat.Png);
            memory.Position = 0;
            var buffer = memory.ToArray();
            await stream.WriteAsync(buffer.AsBuffer()).AsTask(ct).ConfigureAwait(false);
        }
        await stream.FlushAsync().AsTask(ct).ConfigureAwait(false);
        stream.Seek(0);
        
        var decoder = await BitmapDecoder.CreateAsync(stream).AsTask(ct).ConfigureAwait(false);
        var softwareBitmap = await decoder
            .GetSoftwareBitmapAsync(BitmapPixelFormat.Bgra8, BitmapAlphaMode.Premultiplied)
            .AsTask(ct)
            .ConfigureAwait(false);
        preprocessWatch.Stop();

        ct.ThrowIfCancellationRequested();

        var inferenceWatch = Stopwatch.StartNew();
        var ocrResult = await _engine.RecognizeAsync(softwareBitmap).AsTask(ct).ConfigureAwait(false);
        inferenceWatch.Stop();
        
        softwareBitmap.Dispose();

        ct.ThrowIfCancellationRequested();

        // OcrResult → Ocr.OcrResult 変換
        var postprocessWatch = Stopwatch.StartNew();
        var fragments = ocrResult.Lines
            .SelectMany(line => line.Words)
            .Select(word => new OcrFragment(
                word.Text,
                1.0, // Windows.Media.Ocr は信頼度を返さない
                new Rectangle(
                    (int)Math.Round(word.BoundingRect.X),
                    (int)Math.Round(word.BoundingRect.Y),
                    (int)Math.Round(word.BoundingRect.Width),
                    (int)Math.Round(word.BoundingRect.Height))
            ))
            .ToArray();
        postprocessWatch.Stop();

        totalWatch.Stop();

        var timings = new OcrPerformanceTimings(
            preprocessWatch.Elapsed,
            inferenceWatch.Elapsed,
            postprocessWatch.Elapsed);

        return new OcrResult(fragments, totalWatch.Elapsed, timings);
    }
}
