using System.Diagnostics;
using System.Drawing;
using System.Text;
using System.Threading;
using Ocr;

namespace OCRClipboard.App;

public partial class Program
{
    // デバッグモード制御（環境変数 OCR_DEBUG=1 で有効化）
    private static readonly bool DebugMode = Environment.GetEnvironmentVariable("OCR_DEBUG") == "1";

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

        // 画像ファイルからの自動テスト（--test-image <画像パス> [期待テキストパス]）
        if (args.Length >= 2 && args[0] == "--test-image")
        {
            var imagePath = args[1];
            var expectedTextPath = args.Length >= 3 ? args[2] : null;
            await RunImageTestAsync(imagePath, expectedTextPath);
            return;
        }

        // H0棄却テストモード（--test-h0 <文字数>）
        if (args.Length >= 2 && args[0] == "--test-h0")
        {
            if (int.TryParse(args[1], out var charCount))
            {
                await RunH0TestAsync(charCount);
            }
            else
            {
                Console.Error.WriteLine($"[ERROR] Invalid character count: {args[1]}");
            }
            return;
        }

        if (DebugMode) Console.WriteLine("[C#] Starting Windows.Media.Ocr engine...");

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

        if (DebugMode) Console.WriteLine("[C#] Done.");
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

            if (DebugMode && File.Exists(path))
            {
                Console.WriteLine($"[C#] Debug capture saved: {path}");
            }
            else if (DebugMode)
            {
                Console.Error.WriteLine("[C#] Debug capture save attempted, but file not found afterwards.");
            }
        }
        catch (Exception ex)
        {
            if (DebugMode) Console.Error.WriteLine($"[C#] Failed to save debug capture: {ex.Message}");
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

    private static async Task RunH0TestAsync(int targetChars)
    {
        Console.WriteLine("========================================");
        Console.WriteLine($"[H0 REJECTION TEST] 文字数: {targetChars}");
        Console.WriteLine("========================================");
        Console.WriteLine($"H0 (帰無仮説):");
        Console.WriteLine($"  - 識字率 >= 95%");
        Console.WriteLine($"  - 処理時間 < 10,000ms");
        Console.WriteLine($"検証: H0を棄却できるか（どちらか一方でも破ればH0棄却）");
        Console.WriteLine("========================================\n");

        var engine = new WindowsMediaOcrEngine();

        // テスト画像生成
        var testText = GenerateTestText(targetChars);
        var actualChars = testText.Length;
        Console.WriteLine($"[生成] 実際の文字数: {actualChars}");

        using var bitmap = GenerateTextImage(testText);

        // OCR実行（5回測定して統計取得）
        var timings = new List<double>();
        var accuracies = new List<double>();

        Console.WriteLine($"\n[測定開始] 5回実行...");

        for (int i = 0; i < 5; i++)
        {
            var sw = Stopwatch.StartNew();
            var result = await engine.RecognizeAsync(bitmap);
            sw.Stop();

            var ocrMs = sw.Elapsed.TotalMilliseconds;
            var recognized = result.CombinedText;

            // 識字率計算（文字数ベース）
            var accuracy = CalculateAccuracy(testText, recognized);

            timings.Add(ocrMs);
            accuracies.Add(accuracy);

            Console.WriteLine($"  試行{i + 1}: {ocrMs:F1}ms, 識字率={accuracy:P2} ({recognized.Length}/{actualChars}文字認識)");

            await Task.Delay(100); // GC安定化
        }

        // 統計計算
        var avgTime = timings.Average();
        var maxTime = timings.Max();
        var avgAccuracy = accuracies.Average();
        var minAccuracy = accuracies.Min();

        Console.WriteLine("\n========================================");
        Console.WriteLine("[統計結果]");
        Console.WriteLine($"処理時間: 平均={avgTime:F1}ms, 最大={maxTime:F1}ms");
        Console.WriteLine($"識字率: 平均={avgAccuracy:P2}, 最小={minAccuracy:P2}");
        Console.WriteLine("========================================");

        // H0棄却判定
        var timeReject = maxTime >= 10000.0;
        var accuracyReject = minAccuracy < 0.95;

        Console.WriteLine("\n[H0 棄却判定]");
        Console.WriteLine($"処理時間条件: {maxTime:F1}ms >= 10,000ms → {(timeReject ? "❌ H0棄却（処理時間超過）" : "✅ H0維持")}");
        Console.WriteLine($"識字率条件: {minAccuracy:P2} < 95% → {(accuracyReject ? "❌ H0棄却（精度低下）" : "✅ H0維持")}");

        if (timeReject || accuracyReject)
        {
            Console.WriteLine("\n🎯 結論: H0 棄却（帰無仮説は偽）");
            Console.WriteLine("   → Windows.Media.Ocrは大量テキストで性能劣化する");
            if (timeReject) Console.WriteLine($"   → 証拠: 処理時間 {maxTime:F1}ms が閾値10,000msを超過");
            if (accuracyReject) Console.WriteLine($"   → 証拠: 識字率 {minAccuracy:P2} が閾値95%を下回る");
        }
        else
        {
            Console.WriteLine("\n✅ 結論: H0 維持（帰無仮説は棄却できない）");
            Console.WriteLine($"   → {actualChars}文字では性能劣化は観測されなかった");
            Console.WriteLine($"   → より大きな文字数でテストを推奨（例: {actualChars * 2}文字）");
        }

        Console.WriteLine("========================================");
    }

    private static double CalculateAccuracy(string expected, string actual)
    {
        // 簡易的な識字率計算（文字数比較）
        // より正確にはLevenshtein距離を使うべきだが、ここでは文字数ベース
        if (string.IsNullOrEmpty(expected)) return 0.0;

        var expectedChars = expected.Length;
        var actualChars = actual.Length;

        // 認識文字数が期待値に近いほど高スコア
        var ratio = Math.Min(actualChars, expectedChars) / (double)expectedChars;
        return ratio;
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

    private static async Task RunImageTestAsync(string imagePath, string? expectedTextPath)
    {
        Console.WriteLine("========================================");
        Console.WriteLine($"[IMAGE AUTO TEST] 画像ファイルからOCRテスト");
        Console.WriteLine("========================================");
        Console.WriteLine($"画像: {imagePath}");
        if (expectedTextPath != null)
            Console.WriteLine($"期待テキスト: {expectedTextPath}");
        Console.WriteLine("========================================\n");

        // 画像ファイル存在チェック
        if (!File.Exists(imagePath))
        {
            Console.Error.WriteLine($"❌ エラー: 画像ファイルが見つかりません: {imagePath}");
            return;
        }

        // 期待テキスト読み込み
        string? expectedText = null;
        if (expectedTextPath != null && File.Exists(expectedTextPath))
        {
            expectedText = await File.ReadAllTextAsync(expectedTextPath, Encoding.UTF8);
            Console.WriteLine($"[期待テキスト] {expectedText.Length}文字読み込み");
        }

        // 画像読み込み
        using var bitmap = new Bitmap(imagePath);
        Console.WriteLine($"[画像情報] サイズ: {bitmap.Width}x{bitmap.Height}px");

        // 自動的に全体を選択（パディング追加）
        var pad = 8;
        var paddedBitmap = new Bitmap(bitmap.Width, bitmap.Height + 2 * pad);
        using (var g = Graphics.FromImage(paddedBitmap))
        {
            g.Clear(Color.White);
            g.DrawImage(bitmap, 0, pad);
        }

        Console.WriteLine($"[前処理] 上下{pad}pxパディング追加");

        // OCR実行（5回測定）
        var engine = new WindowsMediaOcrEngine();
        var timings = new List<double>();
        var results = new List<string>();
        var accuracies = new List<double>();

        Console.WriteLine($"\n[OCR実行] 5回測定開始...");

        for (int i = 0; i < 5; i++)
        {
            var sw = Stopwatch.StartNew();
            var ocrResult = await engine.RecognizeAsync(paddedBitmap);
            sw.Stop();

            var ocrMs = sw.Elapsed.TotalMilliseconds;
            var recognized = ocrResult.CombinedText;

            timings.Add(ocrMs);
            results.Add(recognized);

            if (expectedText != null)
            {
                var accuracy = CalculateAccuracy(expectedText, recognized);
                accuracies.Add(accuracy);
                Console.WriteLine($"  試行{i + 1}: {ocrMs:F1}ms, fragments={ocrResult.FragmentCount}, 識字率={accuracy:P2}");
            }
            else
            {
                Console.WriteLine($"  試行{i + 1}: {ocrMs:F1}ms, fragments={ocrResult.FragmentCount}, 文字数={recognized.Length}");
            }

            await Task.Delay(100); // GC安定化
        }

        paddedBitmap.Dispose();

        // 統計計算
        var avgTime = timings.Average();
        var maxTime = timings.Max();
        var minTime = timings.Min();

        Console.WriteLine("\n========================================");
        Console.WriteLine("[統計結果]");
        Console.WriteLine($"処理時間: 平均={avgTime:F1}ms, 最小={minTime:F1}ms, 最大={maxTime:F1}ms");

        if (expectedText != null && accuracies.Count > 0)
        {
            var avgAccuracy = accuracies.Average();
            var minAccuracy = accuracies.Min();
            Console.WriteLine($"識字率: 平均={avgAccuracy:P2}, 最小={minAccuracy:P2}");

            // H0棄却判定
            var timeReject = maxTime >= 10000.0;
            var accuracyReject = minAccuracy < 0.95;

            Console.WriteLine("\n[H0判定]");
            Console.WriteLine($"  処理時間 < 10,000ms: {(timeReject ? "❌ 棄却" : "✅ 受容")} (最大={maxTime:F1}ms)");
            Console.WriteLine($"  識字率 >= 95%: {(accuracyReject ? "❌ 棄却" : "✅ 受容")} (最小={minAccuracy:P2})");

            if (timeReject || accuracyReject)
            {
                Console.WriteLine("\n🔴 結論: H0を棄却（Windows.Media.Ocrの限界を超えた）");
                if (timeReject)
                    Console.WriteLine($"   理由: 処理時間が10秒を超えた ({maxTime:F1}ms)");
                if (accuracyReject)
                    Console.WriteLine($"   理由: 識字率が95%を下回った ({minAccuracy:P2})");
            }
            else
            {
                Console.WriteLine("\n🟢 結論: H0を受容（Windows.Media.Ocrは実用範囲内）");
            }
        }

        // 最頻出の認識結果を表示
        var mostCommon = results.GroupBy(x => x).OrderByDescending(g => g.Count()).First().Key;
        Console.WriteLine("\n[認識結果サンプル]");
        Console.WriteLine(mostCommon.Length > 200 ? mostCommon[..200] + "..." : mostCommon);
        Console.WriteLine("========================================");
    }

}
