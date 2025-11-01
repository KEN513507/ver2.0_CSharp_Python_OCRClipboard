using System.Threading.Tasks;
using Tests.Common;
using Xunit;

namespace Tests.Slow;

[Collection("SlowOCR")]
public sealed class WindowsMediaOcrIntegrationTests
{
    [SlowOcr]
    [Fact(Skip = "Windows.Media.Ocr 実装を追加したタイミングで有効化")] 
    public Task RunRealOcrSmokeAsync()
    {
        // TODO: Windows.Media.Ocr の実機テストを実装する。
        // 例: 矩形キャプチャ -> OCR -> クリップボード の E2E を測定。
        return Task.CompletedTask;
    }
}
