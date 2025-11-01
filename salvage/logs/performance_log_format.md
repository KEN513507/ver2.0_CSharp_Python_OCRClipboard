# パフォーマンス計測ログ書式

## 目的
OCR処理の**ボトルネック特定**と**性能劣化の早期検出**。

## ログ書式（stderr出力）

### [PERF] 処理時間の分解
```
[PERF] capture=45ms preproc=12ms infer=823ms postproc=8ms total=888ms
```

- **capture**: 画面キャプチャ（mss/PIL/WinAPI）
- **preproc**: リサイズ・正規化・ノイズ除去
- **infer**: OCRエンジン推論（最重要）
- **postproc**: 信頼度フィルタ・NFKC正規化・品質判定
- **total**: エンドツーエンド時間

### [OCR] 推論結果のサマリ
```
[OCR] n_fragments=3 mean_conf=0.87 min_conf=0.72 n_filtered=0
```

- **n_fragments**: 検出されたテキスト断片数
- **mean_conf**: 平均信頼度
- **min_conf**: 最低信頼度（閾値比較用）
- **n_filtered**: 閾値で除外された断片数

## 実装例（Python）
```python
import sys
import time

class PerfLogger:
    def __init__(self):
        self.times = {}
        self.start_time = None
    
    def mark(self, label: str):
        now = time.perf_counter()
        if self.start_time is None:
            self.start_time = now
        else:
            elapsed = (now - self.prev_time) * 1000  # ms
            self.times[label] = elapsed
        self.prev_time = now
    
    def log_perf(self):
        parts = [f"{k}={int(v)}ms" for k, v in self.times.items()]
        total = int(sum(self.times.values()))
        parts.append(f"total={total}ms")
        print(f"[PERF] {' '.join(parts)}", file=sys.stderr)

# 使用例
perf = PerfLogger()
perf.mark("start")
img = capture_screen()
perf.mark("capture")
img = preprocess(img)
perf.mark("preproc")
result = ocr_engine.recognize(img)
perf.mark("infer")
filtered = post_process(result)
perf.mark("postproc")
perf.log_perf()
```

## C# 移植例
```csharp
using System.Diagnostics;

public class PerfLogger
{
    private Stopwatch sw = Stopwatch.StartNew();
    private Dictionary<string, long> times = new();
    
    public void Mark(string label)
    {
        times[label] = sw.ElapsedMilliseconds;
    }
    
    public void LogPerf()
    {
        var parts = times.Select(kv => $"{kv.Key}={kv.Value}ms");
        var total = times.Values.Sum();
        Console.Error.WriteLine($"[PERF] {string.Join(" ", parts)} total={total}ms");
    }
}
```

## 集計スクリプト（分析用）
```python
import re
import statistics

def parse_perf_logs(log_file: str):
    """[PERF]行から統計を抽出"""
    pattern = r'\[PERF\] .* total=(\d+)ms'
    totals = []
    with open(log_file) as f:
        for line in f:
            if m := re.search(pattern, line):
                totals.append(int(m.group(1)))
    
    print(f"実行回数: {len(totals)}")
    print(f"平均: {statistics.mean(totals):.1f}ms")
    print(f"中央値: {statistics.median(totals):.1f}ms")
    print(f"最小/最大: {min(totals)}ms / {max(totals)}ms")
```

## 適用場面
- **ウォームアップ検証**（初回 vs 2回目以降）
- **モデル比較**（mobile vs server）
- **環境依存調査**（CPU/GPU、DPI、画像サイズ）
- **リグレッション検出**（CI で平均時間を監視）

## 出力先
- **開発時**: stderr（ターミナル即表示）
- **本番**: ファイル（`logs/perf_YYYYMMDD.log`）
- **分析**: JSON出力も検討（構造化ログ）
