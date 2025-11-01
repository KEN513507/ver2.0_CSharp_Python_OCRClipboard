using System.Diagnostics;
using System.Text;

namespace OCRClipboard.App;

/// <summary>
/// OCR性能モニタリングとSLA guard実装
/// 二次関数モデル: y = 0.0010277886x² - 0.3301546922x + 113.3679999142 (R²=0.978, AIC=57.18)
/// </summary>
public sealed class OcrPerformanceMonitor
{
    // 二次関数係数 (AICベスト: 57.18 vs 線形: 67.40)
    private const double A = 0.0010277886;
    private const double B = -0.3301546922;
    private const double C = 113.3679999142;

    // SLA閾値: 400ms @ 630文字前後
    private const int SlaThresholdMs = 400;
    private const int SafeCharsLimit = 630; // 400ms達成可能な最大文字数

    private readonly List<PerformanceRecord> _records = new();
    private readonly object _lock = new();

    public sealed class PerformanceRecord
    {
        public DateTime Timestamp { get; init; }
        public int InputChars { get; init; }
        public double PredictedMs { get; init; }
        public double ActualMs { get; init; }
        public double ResidualMs { get; init; }
        public bool ExceedsSla { get; init; }
        public bool WasAutoSplit { get; init; }
    }

    /// <summary>
    /// 二次関数モデルで処理時間を予測
    /// </summary>
    public double PredictProcessingTime(int charCount)
    {
        return A * charCount * charCount + B * charCount + C;
    }

    /// <summary>
    /// SLA閾値超過判定
    /// </summary>
    public bool ExceedsSla(int charCount)
    {
        return PredictProcessingTime(charCount) > SlaThresholdMs;
    }

    /// <summary>
    /// テキストを安全なチャンクに自動分割
    /// </summary>
    public IEnumerable<string> ChunkByChars(string text, int limit = SafeCharsLimit)
    {
        for (int i = 0; i < text.Length; i += limit)
        {
            yield return text.Substring(i, Math.Min(limit, text.Length - i));
        }
    }

    /// <summary>
    /// OCR処理を実測してレコード記録
    /// </summary>
    public async Task<T> MeasureAsync<T>(int charCount, Func<Task<T>> ocrTask, bool wasAutoSplit = false)
    {
        var sw = Stopwatch.StartNew();
        var result = await ocrTask();
        sw.Stop();

        var predictedMs = PredictProcessingTime(charCount);
        var actualMs = sw.Elapsed.TotalMilliseconds;
        var residualMs = actualMs - predictedMs;

        var record = new PerformanceRecord
        {
            Timestamp = DateTime.UtcNow,
            InputChars = charCount,
            PredictedMs = predictedMs,
            ActualMs = actualMs,
            ResidualMs = residualMs,
            ExceedsSla = actualMs > SlaThresholdMs,
            WasAutoSplit = wasAutoSplit
        };

        lock (_lock)
        {
            _records.Add(record);
        }

        return result;
    }

    /// <summary>
    /// モニタリングレポート生成
    /// </summary>
    public string GenerateReport()
    {
        lock (_lock)
        {
            if (_records.Count == 0)
                return "No performance data collected yet.";

            var sb = new StringBuilder();
            sb.AppendLine("═══════════════════════════════════════════════════════════════");
            sb.AppendLine("📊 OCR Performance Monitoring Report");
            sb.AppendLine("═══════════════════════════════════════════════════════════════");
            sb.AppendLine($"Model: y = {A}x² + {B}x + {C:F2}");
            sb.AppendLine($"SLA Threshold: {SlaThresholdMs}ms @ {SafeCharsLimit} chars");
            sb.AppendLine($"Total Requests: {_records.Count}");
            sb.AppendLine();

            // 統計サマリー
            var actualTimes = _records.Select(r => r.ActualMs).ToArray();
            var residuals = _records.Select(r => r.ResidualMs).ToArray();
            var slaExceeds = _records.Count(r => r.ExceedsSla);
            var autoSplits = _records.Count(r => r.WasAutoSplit);

            sb.AppendLine("📈 Timing Statistics:");
            sb.AppendLine($"  Actual:    Mean={Mean(actualTimes):F1}ms, P95={Percentile(actualTimes, 0.95):F1}ms, P99={Percentile(actualTimes, 0.99):F1}ms, Max={actualTimes.Max():F1}ms");
            sb.AppendLine($"  Residual:  Mean={Mean(residuals):F1}ms, σ={StdDev(residuals):F1}ms");
            sb.AppendLine();

            sb.AppendLine("⚠️ SLA Compliance:");
            sb.AppendLine($"  Exceeded:  {slaExceeds}/{_records.Count} ({100.0 * slaExceeds / _records.Count:F1}%)");
            sb.AppendLine($"  Auto-Split:{autoSplits}/{_records.Count} ({100.0 * autoSplits / _records.Count:F1}%)");
            sb.AppendLine();

            // 最近の10件
            sb.AppendLine("🕐 Recent 10 Requests:");
            sb.AppendLine("  Timestamp            | Chars | Predicted | Actual | Residual | SLA | Split");
            sb.AppendLine("  ---------------------|-------|-----------|--------|----------|-----|------");
            foreach (var r in _records.TakeLast(10))
            {
                var slaMarker = r.ExceedsSla ? "❌" : "✅";
                var splitMarker = r.WasAutoSplit ? "🔪" : "  ";
                sb.AppendLine($"  {r.Timestamp:HH:mm:ss.fff} | {r.InputChars,5} | {r.PredictedMs,7:F1}ms | {r.ActualMs,6:F1}ms | {r.ResidualMs,7:+0.0;-0.0}ms | {slaMarker}  | {splitMarker}");
            }

            sb.AppendLine("═══════════════════════════════════════════════════════════════");
            return sb.ToString();
        }
    }

    /// <summary>
    /// 評価用レポート生成 (ΔAIC, 残差分布必須)
    /// </summary>
    public string GenerateEvaluationReport()
    {
        lock (_lock)
        {
            if (_records.Count < 7) // 最低限のサンプル数
                return "Insufficient data for evaluation (need at least 7 samples).";

            var sb = new StringBuilder();
            sb.AppendLine("═══════════════════════════════════════════════════════════════");
            sb.AppendLine("📐 Model Evaluation Report");
            sb.AppendLine("═══════════════════════════════════════════════════════════════");
            
            // モデル情報
            sb.AppendLine("🔬 Quadratic Model (Selected):");
            sb.AppendLine($"  Equation: y = {A}x² + {B}x + {C:F2}");
            sb.AppendLine($"  AIC: 57.18 (vs Linear: 67.40, ΔAIC=10.22 → 'almost certain')");
            sb.AppendLine($"  R²: 0.978 (vs Linear: 0.876)");
            sb.AppendLine($"  Complexity: O(n²) due to fragment interference");
            sb.AppendLine();

            // 残差分布 (必須)
            var residuals = _records.Select(r => r.ResidualMs).ToArray();
            var residualMean = Mean(residuals);
            var residualStdDev = StdDev(residuals);
            var residualMax = residuals.Max(Math.Abs);

            sb.AppendLine("📊 Residual Distribution (Required):");
            sb.AppendLine($"  Mean:   {residualMean:F2}ms");
            sb.AppendLine($"  σ:      {residualStdDev:F2}ms");
            sb.AppendLine($"  Max:    {residualMax:F2}ms");
            sb.AppendLine($"  Range:  [{residuals.Min():F1}, {residuals.Max():F1}]ms");
            sb.AppendLine();

            // 実測データとの適合度
            var actualTimes = _records.Select(r => r.ActualMs).ToArray();
            var predictedTimes = _records.Select(r => r.PredictedMs).ToArray();
            var ss_res = residuals.Sum(r => r * r);
            var ss_tot = actualTimes.Sum(a => Math.Pow(a - Mean(actualTimes), 2));
            var r_squared = 1 - ss_res / ss_tot;

            sb.AppendLine("✅ Model Fit:");
            sb.AppendLine($"  R² (observed): {r_squared:F6}");
            sb.AppendLine($"  SS_res: {ss_res:F1}");
            sb.AppendLine($"  SS_tot: {ss_tot:F1}");
            sb.AppendLine();

            // 警告: R²単独使用禁止
            sb.AppendLine("⚠️ Validation Note:");
            sb.AppendLine("  ΔAIC (10.22) used for model selection, NOT R² alone.");
            sb.AppendLine("  R² without AIC/BIC risks overfitting.");
            sb.AppendLine("═══════════════════════════════════════════════════════════════");
            
            return sb.ToString();
        }
    }

    // 統計ヘルパー
    private static double Mean(double[] values) =>
        values.Length > 0 ? values.Average() : 0;

    private static double StdDev(double[] values)
    {
        if (values.Length < 2) return 0;
        var mean = Mean(values);
        return Math.Sqrt(values.Sum(v => Math.Pow(v - mean, 2)) / (values.Length - 1));
    }

    private static double Percentile(double[] values, double percentile)
    {
        if (values.Length == 0) return 0;
        var sorted = values.OrderBy(v => v).ToArray();
        var index = (int)Math.Ceiling(percentile * sorted.Length) - 1;
        return sorted[Math.Max(0, Math.Min(index, sorted.Length - 1))];
    }
}
