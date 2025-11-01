using System.Drawing;
using System.Threading;
using System.Threading.Tasks;

namespace Ocr;

/// <summary>
/// テストを高速に回すためのフェイク OCR 実装。
/// Python 版の autouse モックと等価の役割を担う。
/// </summary>
public sealed class FakeOcrEngine : IOcrEngine
{
    public Task<OcrResult> RecognizeAsync(Bitmap bitmap, CancellationToken ct = default)
    {
        var fragments = new[]
        {
            new OcrFragment("テスト", 0.99, Rectangle.Empty),
        };
        var timings = new OcrPerformanceTimings(
            Preprocess: TimeSpan.Zero,
            Inference: TimeSpan.FromMilliseconds(5),
            Postprocess: TimeSpan.Zero);
        return Task.FromResult(new OcrResult(fragments, TimeSpan.FromMilliseconds(5), timings));
    }
}
