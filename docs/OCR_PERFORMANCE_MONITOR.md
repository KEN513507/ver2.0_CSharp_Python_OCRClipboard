# OCR Performance Monitor

二次関数モデル（y = 0.001028x² - 0.3302x + 113.37）に基づくSLA guard実装とパフォーマンスモニタリングシステム。

## 統計モデルの根拠

- **モデル選択**: ΔAIC = 10.22 (二次 vs 線形) → "almost certain" 二次が優位
- **適合度**: R² = 0.978 (二次) vs R² = 0.876 (線形)
- **複雑性**: O(n²) - フラグメント間干渉コストに起因
- **遷移点**: 500-800文字で O(n) → O(n²) 移行

## 主要機能

### 1. 処理時間予測
```csharp
var monitor = new OcrPerformanceMonitor();
double predictedMs = monitor.PredictProcessingTime(charCount: 560);
// => 約400ms（SLA閾値付近）
```

### 2. SLA閾値チェック
```csharp
bool needsSplit = monitor.ExceedsSla(charCount: 600);
// => true（600文字は400msを超過）
```

### 3. 自動チャンク分割
```csharp
string longText = "..."; // 2000文字
foreach (var chunk in monitor.ChunkByChars(longText, limit: 560))
{
    // 各チャンクは560文字以下（SLA準拠）
    await ProcessOcrAsync(chunk);
}
```

### 4. パフォーマンス計測
```csharp
var result = await monitor.MeasureAsync(
    charCount: estimatedChars,
    ocrTask: async () => await client.CallAsync<OcrResponse>(...),
    wasAutoSplit: false
);

// 自動的にレコード記録
// - InputChars, PredictedMs, ActualMs, ResidualMs
// - ExceedsSla, WasAutoSplit
```

### 5. モニタリングレポート
```csharp
string report = monitor.GenerateReport();
Console.WriteLine(report);
```

出力例:
```
═══════════════════════════════════════════════════════════════
📊 OCR Performance Monitoring Report
═══════════════════════════════════════════════════════════════
Model: y = 0.001028x² + -0.3302x + 113.37
SLA Threshold: 400ms @ 560 chars
Total Requests: 15

📈 Timing Statistics:
  Actual:    Mean=245.3ms, P95=512.1ms, P99=852.6ms, Max=852.6ms
  Residual:  Mean=-2.1ms, σ=38.7ms

⚠️ SLA Compliance:
  Exceeded:  3/15 (20.0%)
  Auto-Split:2/15 (13.3%)

🕐 Recent 10 Requests:
  Timestamp            | Chars | Predicted | Actual | Residual | SLA | Split
  ---------------------|-------|-----------|--------|----------|-----|------
  14:23:45.123 |   100 |    81.0ms |   85.2ms |   +4.2ms | ✅  |   
  14:24:12.456 |   500 |   214.8ms |  220.1ms |   +5.3ms | ✅  |   
  14:25:01.789 |   800 |   431.8ms |  445.6ms |  +13.8ms | ❌  |   
  14:26:34.012 |  1000 |   852.6ms |  870.2ms |  +17.6ms | ❌  | 🔪
═══════════════════════════════════════════════════════════════
```

### 6. 評価レポート（統計的厳密性）
```csharp
string evalReport = monitor.GenerateEvaluationReport();
Console.WriteLine(evalReport);
```

出力例:
```
═══════════════════════════════════════════════════════════════
📐 Model Evaluation Report
═══════════════════════════════════════════════════════════════
🔬 Quadratic Model (Selected):
  Equation: y = 0.001028x² + -0.3302x + 113.37
  AIC: 57.18 (vs Linear: 67.40, ΔAIC=10.22 → 'almost certain')
  R²: 0.978 (vs Linear: 0.876)
  Complexity: O(n²) due to fragment interference

📊 Residual Distribution (Required):
  Mean:   -2.15ms
  σ:      38.72ms
  Max:    87.34ms
  Range:  [-92.7, 87.3]ms

✅ Model Fit:
  R² (observed): 0.978357
  SS_res: 14987.2
  SS_tot: 692341.8

⚠️ Validation Note:
  ΔAIC (10.22) used for model selection, NOT R² alone.
  R² without AIC/BIC risks overfitting.
═══════════════════════════════════════════════════════════════
```

## 統計的妥当性の保証

### なぜ二次モデルか？

1. **AIC比較**: ΔAIC = 10.22 → Burnham & Anderson (2002) の基準で "almost certain"
2. **物理的根拠**: フラグメント間干渉コスト ∝ fragments²（R² = 0.970）
3. **遷移観測**: 500→800文字で 0.723→2.104 ms/文字増分（非線形化開始）

### R²単独使用の禁止

- R² = 0.978 だけでは過学習リスクあり
- AIC/BICによるペナルティ付き選択が必須
- 残差分布（mean, σ, max）の確認が必須

## 実装例

### Program.cs での統合

```csharp
public partial class Program
{
    private static readonly OcrPerformanceMonitor _monitor = new();

    public static async Task Main(string[] args)
    {
        // ... 初期化 ...

        // SLA guard チェック
        int estimatedChars = EstimateCharsFromImage(imageBase64);
        
        if (_monitor.ExceedsSla(estimatedChars))
        {
            Console.WriteLine($"⚠️ SLA exceeded: {estimatedChars} chars");
            
            // 自動分割
            var chunks = _monitor.ChunkByChars(text, limit: 560);
            var results = new List<OcrResponse>();
            
            foreach (var chunk in chunks)
            {
                var result = await _monitor.MeasureAsync(
                    chunk.Length,
                    async () => await ProcessOcrChunk(chunk),
                    wasAutoSplit: true
                );
                results.Add(result);
            }
            
            var combinedText = string.Join("", results.Select(r => r.Text));
        }
        else
        {
            // 単一リクエストで処理
            var result = await _monitor.MeasureAsync(
                estimatedChars,
                async () => await ProcessOcr(imageBase64),
                wasAutoSplit: false
            );
        }

        // レポート出力
        Console.WriteLine(_monitor.GenerateReport());
        Console.WriteLine(_monitor.GenerateEvaluationReport());
    }
}
```

## メトリクス定義

| メトリクス | 説明 | 用途 |
|------------|------|------|
| **PredictedMs** | 二次関数モデルによる予測時間 | SLA guard事前判定 |
| **ActualMs** | 実測処理時間 | 実績記録 |
| **ResidualMs** | ActualMs - PredictedMs | モデル精度検証 |
| **ExceedsSla** | ActualMs > 400ms | SLA違反検出 |
| **WasAutoSplit** | 自動分割実施フラグ | 分割効果分析 |
| **P95/P99** | 95/99パーセンタイル | SLO設定根拠 |

## SLA閾値設定の根拠

- **閾値**: 400ms @ 560文字
- **安全マージン**: 二次関数で560文字 → 約400ms（安全側に丸め）
- **遷移点**: 500-800文字で急増開始（データ実測）
- **自動分割**: 560文字/チャンク = 各チャンク400ms以内

## 参照

- `scripts/plot_benchmark.py`: ベンチマークグラフ生成
- `TECHNICAL_LIMITS.md`: 技術的制限事項（O(n²)挙動）
- `BENCHMARK.md`: ベンチマーク実行手順
- 統計モデル評価: ΔAIC=10.22, R²=0.978, 残差σ=38.7ms
