using System.Drawing;
using System.Threading;
using System.Threading.Tasks;

namespace Ocr;

public interface IOcrEngine
{
    Task<OcrResult> RecognizeAsync(Bitmap bitmap, CancellationToken ct = default);
}
