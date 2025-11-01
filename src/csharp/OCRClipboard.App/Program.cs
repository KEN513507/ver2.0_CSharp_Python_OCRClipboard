using System.Diagnostics;
using System.Drawing;
using System.Text;
using System.Threading;
using Ocr;

namespace OCRClipboard.App;

public partial class Program
{
    public static async Task Main(string[] args)
    {
        // CLI文字化け対策: UTF-8エンコーディング強制
        Console.OutputEncoding = Encoding.UTF8;
        Console.InputEncoding = Encoding.UTF8;

        // ベンチマークモード検出
        if (args.Length > 0 && args[0] == "--benchmark")
        {
            await RunBenchmarkAsync();
            return;
        }

        Console.WriteLine("[C#] Starting Windows.Media.Ocr engine...");

        var engine = new WindowsMediaOcrEngine();

        var swWall = Stopwatch.StartNew();
        var swUser = Stopwatch.StartNew();

        // USER: オーバーレイ表示〜マウスアップまで（人間の操作時間）
        var selection = await OCRClipboard.Overlay.OverlayRunner.RunSelectionCaptureAsync();
        swUser.Stop();

        if (selection != null)
        {
            // GRAB: 画面から画像を切り出す時間だけ
            var swGrab = Stopwatch.StartNew();
            SaveDebugCapture(selection.Value.imageBase64);

            // Base64 → Bitmap
            var imageBytes = Convert.FromBase64String(selection.Value.imageBase64);
            using var ms = new System.IO.MemoryStream(imageBytes);
            using var bitmap = new Bitmap(ms);
            swGrab.Stop();

            // クロップ妥当性チェック（下端欠け防止）
            var width = bitmap.Width;
            var height = bitmap.Height;
            if (height < 40 || width / (double)height > 25.0)
            {
                Console.Error.WriteLine($"[WARN] Selection too thin (W={width} H={height}); OCR may fail. Consider reselecting.");
            }

            // PRE: 上下パディング追加（下端欠け対策）
            var swPre = Stopwatch.StartNew();
            var pad = 8;
            var paddedBitmap = new Bitmap(width, height + 2 * pad);
            using (var g = System.Drawing.Graphics.FromImage(paddedBitmap))
            {
                g.Clear(System.Drawing.Color.White);
                g.DrawImage(bitmap, 0, pad);
            }
            swPre.Stop();

            // OCR: 推論実行
            var swOcr = Stopwatch.StartNew();
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
            swOcr.Stop();

            // POST: クリップボードコピー
            var swPost = Stopwatch.StartNew();
            var combinedText = ocrResult.CombinedText;
            var clipboardCopied = false;
            if (!string.IsNullOrEmpty(combinedText))
            {
                TrySetClipboardText(combinedText);
                clipboardCopied = true;
            }
            swPost.Stop();

            swWall.Stop();

            // タイミング計算
            var userMs = swUser.Elapsed.TotalMilliseconds;
            var grabMs = swGrab.Elapsed.TotalMilliseconds;
            var preMs = swPre.Elapsed.TotalMilliseconds;
            var ocrMs = swOcr.Elapsed.TotalMilliseconds;
            var postMs = swPost.Elapsed.TotalMilliseconds;
            var procTotal = grabMs + preMs + ocrMs + postMs;
            var wallTotal = swWall.Elapsed.TotalMilliseconds;

            // 人間が読みやすいログ形式
            Console.Error.WriteLine("================================================");
            Console.Error.WriteLine($"[タイミング分析] proc_total={procTotal:F0}ms (SLA目標: <400ms)");
            Console.Error.WriteLine($"  ├─ user      : {userMs:F0}ms  (人間の選択時間 - 評価対象外)");
            Console.Error.WriteLine($"  ├─ grab      : {grabMs:F0}ms  (画像取得)");
            Console.Error.WriteLine($"  ├─ pre       : {preMs:F0}ms  (前処理)");
            Console.Error.WriteLine($"  ├─ ocr       : {ocrMs:F0}ms  (OCR推論) ★重要");
            Console.Error.WriteLine($"  ├─ post      : {postMs:F0}ms  (後処理)");
            Console.Error.WriteLine($"  └─ wall_total: {wallTotal:F0}ms (全体 - 参考値)");
            Console.Error.WriteLine($"[OCR結果] fragments={ocrResult.FragmentCount}, confidence={ocrResult.MeanConfidence:F2}");
            Console.Error.WriteLine($"[テキスト全文]");
            Console.Error.WriteLine(combinedText);
            Console.Error.WriteLine($"[クリップボード] コピー={clipboardCopied}, 文字数={combinedText.Length}");
            Console.Error.WriteLine("================================================");
            
            // 機械処理用の固定フォーマット（互換性維持・24文字サンプル）
            var sample = combinedText.Length > 24 
                ? combinedText[..24] + "…" 
                : combinedText;
            Console.Error.WriteLine(
                $"[PERF] user={userMs:F0}ms grab={grabMs:F0}ms pre={preMs:F0}ms ocr={ocrMs:F0}ms post={postMs:F0}ms proc_total={procTotal:F0}ms wall_total={wallTotal:F0}ms");
            Console.Error.WriteLine(
                $"[OCR] n_fragments={ocrResult.FragmentCount} mean_conf={ocrResult.MeanConfidence:F2} sample=\"{sample}\"");
        }

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
    
    private static async Task RunBenchmarkAsync()
    {
        Console.WriteLine("[BENCHMARK] 文字数 vs OCR処理時間の線形性検証");
        Console.WriteLine("================================================");
        
        var engine = new WindowsMediaOcrEngine();
        var results = new List<(int chars, int fragments, double ocrMs)>();

        // テストパターン: 異なる文字数の画像を生成
        var testSizes = new[] { 50, 100, 200, 300, 500, 800, 1000 };
        
        foreach (var targetChars in testSizes)
        {
            // テスト画像生成（繰り返しテキスト）
            var testText = GenerateTestText(targetChars);
            var bitmap = GenerateTextImage(testText);
            
            // ウォームアップ（初回の遅延を排除）
            if (results.Count == 0)
            {
                await engine.RecognizeAsync(bitmap);
            }
            
            // 実測（3回平均）
            var timings = new List<double>();
            OcrResult? lastResult = null;
            
            for (int i = 0; i < 3; i++)
            {
                var sw = Stopwatch.StartNew();
                lastResult = await engine.RecognizeAsync(bitmap);
                sw.Stop();
                timings.Add(sw.Elapsed.TotalMilliseconds);
                await Task.Delay(100); // GC安定化
            }
            
            var avgMs = timings.Average();
            var actualChars = lastResult!.CombinedText.Length;
            var fragments = lastResult.FragmentCount;
            
            results.Add((actualChars, fragments, avgMs));
            Console.WriteLine($"文字数: {actualChars,4} | fragments: {fragments,3} | OCR時間: {avgMs,6:F1}ms");
            
            bitmap.Dispose();
        }
        
        Console.WriteLine("================================================");
        Console.WriteLine("[分析] 線形回帰による検証");
        
        // 線形回帰: y = ax + b (y=OCR時間, x=文字数)
        var n = results.Count;
        var sumX = results.Sum(r => (double)r.chars);
        var sumY = results.Sum(r => r.ocrMs);
        var sumXY = results.Sum(r => r.chars * r.ocrMs);
        var sumX2 = results.Sum(r => (double)r.chars * r.chars);
        
        var a = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
        var b = (sumY - a * sumX) / n;
        
        Console.WriteLine($"回帰式: OCR時間(ms) = {a:F3} * 文字数 + {b:F1}");
        Console.WriteLine($"解釈: 文字が1増えるごとに {a:F3}ms 増加");
        
        // 決定係数 R²（線形性の強さ）
        var meanY = sumY / n;
        var ssTotal = results.Sum(r => Math.Pow(r.ocrMs - meanY, 2));
        var ssRes = results.Sum(r => Math.Pow(r.ocrMs - (a * r.chars + b), 2));
        var r2 = 1 - (ssRes / ssTotal);
        
        Console.WriteLine($"決定係数 R² = {r2:F4} (1に近いほど線形)");
        
        if (r2 > 0.95)
            Console.WriteLine("✅ 結論: ほぼ完全な線形関係（文字数と処理時間は比例）");
        else if (r2 > 0.85)
            Console.WriteLine("⚠️  結論: おおむね線形（やや非線形要素あり）");
        else
            Console.WriteLine("❌ 結論: 線形ではない（文字数以外の要因が支配的）");
        
        Console.WriteLine("================================================");
        Console.WriteLine("[CSVデータ] グラフ化用");
        Console.WriteLine("文字数,fragments,OCR時間ms");
        foreach (var (chars, fragments, ocrMs) in results)
        {
            Console.WriteLine($"{chars},{fragments},{ocrMs:F1}");
        }
    }
    
    private static string GenerateTestText(int targetChars)
    {
        var baseText = "これはOCRベンチマークテストです。文字数と処理時間の関係を検証します。";
        var sb = new StringBuilder();
        
        while (sb.Length < targetChars)
        {
            sb.Append(baseText);
        }
        
        return sb.ToString()[..Math.Min(targetChars, sb.Length)];
    }
    
    private static Bitmap GenerateTextImage(string text)
    {
        var bitmap = new Bitmap(1200, 800);
        using var g = Graphics.FromImage(bitmap);
        g.Clear(Color.White);
        
        var font = new Font("メイリオ", 14);
        var brush = new SolidBrush(Color.Black);
        var rect = new RectangleF(20, 20, 1160, 760);
        
        g.DrawString(text, font, brush, rect);
        
        return bitmap;
    }
    
}
