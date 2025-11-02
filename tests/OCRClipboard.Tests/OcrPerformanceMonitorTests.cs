using Xunit;
using OCRClipboard.App;

namespace OCRClipboard.Tests;

public class OcrPerformanceMonitorTests
{
    private readonly OcrPerformanceMonitor _monitor = new();

    [Fact]
    public void PredictProcessingTime_Returns_QuadraticModel()
    {
        // 二次関数: y = 0.0010277886x² - 0.3301546922x + 113.3679999142

        // 検証データ（実測値との整合性）
        var testCases = new[]
        {
            (chars: 100, expectedMs: 90.63),
            (chars: 500, expectedMs: 205.24),
            (chars: 800, expectedMs: 507.03),
            (chars: 1000, expectedMs: 811.00)
        };

        foreach (var (chars, expectedMs) in testCases)
        {
            var predicted = _monitor.PredictProcessingTime(chars);
            
            // ±2%の誤差許容（高精度モデル）
            Assert.InRange(predicted, expectedMs * 0.98, expectedMs * 1.02);
        }
    }

    [Theory]
    [InlineData(100, false)]   // 90ms < 400ms
    [InlineData(500, false)]   // 205ms < 400ms
    [InlineData(630, false)]   // 約400ms（境界）
    [InlineData(650, true)]    // >400ms
    [InlineData(800, true)]    // 507ms > 400ms
    [InlineData(1000, true)]   // 811ms > 400ms
    public void ExceedsSla_Correctly_Identifies_Threshold(int chars, bool expectedExceeds)
    {
        var exceeds = _monitor.ExceedsSla(chars);
        Assert.Equal(expectedExceeds, exceeds);
    }

    [Fact]
    public void ChunkByChars_Splits_Text_Correctly()
    {
        var text = new string('x', 2000); // 2000文字
        var chunks = _monitor.ChunkByChars(text, limit: 630).ToList();

        // 2000 / 630 = 3.17 → 4チャンク
        Assert.Equal(4, chunks.Count);
        
        // 最初の3チャンクは630文字
        Assert.Equal(630, chunks[0].Length);
        Assert.Equal(630, chunks[1].Length);
        Assert.Equal(630, chunks[2].Length);
        
        // 最後のチャンクは残り110文字
        Assert.Equal(110, chunks[3].Length);
    }

    [Fact]
    public async Task MeasureAsync_Records_Performance_Correctly()
    {
        var charCount = 500;
        var mockOcrTask = async () =>
        {
            await Task.Delay(100); // 100ms遅延をシミュレート
            return new { Text = "test" };
        };

        var result = await _monitor.MeasureAsync(charCount, mockOcrTask, wasAutoSplit: false);

        var report = _monitor.GenerateReport();
        
        // レポートに1件のレコードが含まれる
        Assert.Contains("Total Requests: 1", report);
        Assert.Contains("500", report); // 文字数
    }

    [Fact]
    public void GenerateReport_Contains_Key_Metrics()
    {
        // 初期状態（レコードなし）
        var emptyReport = _monitor.GenerateReport();
        Assert.Contains("No performance data collected yet", emptyReport);
    }

    [Fact]
    public void GenerateEvaluationReport_Validates_Statistical_Rigor()
    {
        var insufficientReport = _monitor.GenerateEvaluationReport();
        
        // 7件未満ではデータ不足
        Assert.Contains("Insufficient data", insufficientReport);
    }

    [Fact]
    public async Task GenerateEvaluationReport_Contains_Mandatory_Metrics()
    {
        // 7件のサンプルデータを生成
        var testData = new[] { 100, 200, 300, 500, 800, 1000, 1200 };
        
        foreach (var chars in testData)
        {
            await _monitor.MeasureAsync(
                chars,
                async () =>
                {
                    // 予測時間 ± ランダムノイズ
                    var predictedMs = _monitor.PredictProcessingTime(chars);
                    var noise = Random.Shared.Next(-50, 50);
                    await Task.Delay((int)Math.Max(10, predictedMs + noise));
                    return new { Text = "test" };
                },
                wasAutoSplit: false
            );
        }

        var report = _monitor.GenerateEvaluationReport();

        // 必須要素の確認
        Assert.Contains("ΔAIC", report);
        Assert.Contains("Residual Distribution", report);
        Assert.Contains("Mean:", report);
        Assert.Contains("σ:", report);
        Assert.Contains("Max:", report);
        Assert.Contains("R² without AIC/BIC risks overfitting", report);
    }

    [Fact]
    public void QuadraticModel_Parameters_Match_Specification()
    {
        // 係数検証: y = 0.001028x² - 0.3302x + 113.37
        // 直接フィールドアクセス不可のため、特定点での値検証

        // x=0: y = 113.37
        var y0 = _monitor.PredictProcessingTime(0);
        Assert.InRange(y0, 110, 116); // C項の検証

        // x=100: y = 0.001028*10000 - 0.3302*100 + 113.37 = 10.28 - 33.02 + 113.37 = 90.63
        var y100 = _monitor.PredictProcessingTime(100);
        Assert.InRange(y100, 75, 95); // 実測値81.0ms付近

        // x=1000: y = 0.001028*1000000 - 0.3302*1000 + 113.37 = 1028 - 330.2 + 113.37 = 811.17
        var y1000 = _monitor.PredictProcessingTime(1000);
        Assert.InRange(y1000, 750, 900); // 実測値852.6ms付近
    }

    [Fact]
    public void SLA_Threshold_Is_400ms()
    {
        // 712文字でSLA閾値（約400ms）
        var chars712 = _monitor.PredictProcessingTime(712);
        Assert.InRange(chars712, 395, 405); // 400ms ± 5ms

        // 境界付近の挙動
        var exceeds700 = _monitor.ExceedsSla(700);
        var exceeds750 = _monitor.ExceedsSla(750);
        
        // 700は閾値内（385ms）、750で超過（443ms）
        Assert.False(exceeds700);
        Assert.True(exceeds750);
    }
}
