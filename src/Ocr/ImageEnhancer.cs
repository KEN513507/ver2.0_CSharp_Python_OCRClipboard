using System.Drawing;
using System.Drawing.Imaging;

namespace Ocr;

/// <summary>
/// OCR精度向上のための画像前処理クラス
/// 
/// 目的: 識字率 93% → 95% への改善
/// 対象エラー:
/// - 低コントラスト文字の誤認識 (AI → A日)
/// - 全角記号の誤認識 (， → ′)
/// - 小サイズ文字の読み取りミス
/// </summary>
public static class ImageEnhancer
{
    /// <summary>
    /// コントラスト強化 + ガンマ補正
    /// 
    /// 期待効果: 識字率 +1.5-2.5% (93% → 94.5-95.5%)
    /// 処理時間: 約 +30-50ms
    /// 
    /// 適用条件:
    /// - 低コントラスト画像（背景と文字の差が小さい）
    /// - スクリーンショット全般
    /// </summary>
    /// <param name="source">元画像</param>
    /// <returns>コントラスト強化済み画像</returns>
    public static Bitmap EnhanceContrast(Bitmap source)
    {
        var enhanced = new Bitmap(source.Width, source.Height);

        using (var g = Graphics.FromImage(enhanced))
        {
            // コントラスト強化: 1.3倍 (1.2倍だと効果弱い)
            // ガンマ補正: -0.15 (明るさ微調整)
            var colorMatrix = new ColorMatrix(new float[][]
            {
                new float[] {1.3f, 0, 0, 0, 0},      // R
                new float[] {0, 1.3f, 0, 0, 0},      // G
                new float[] {0, 0, 1.3f, 0, 0},      // B
                new float[] {0, 0, 0, 1, 0},         // A (透明度)
                new float[] {-0.15f, -0.15f, -0.15f, 0, 1} // オフセット
            });

            var attributes = new ImageAttributes();
            attributes.SetColorMatrix(colorMatrix);

            g.DrawImage(
                source,
                new Rectangle(0, 0, source.Width, source.Height),
                0, 0, source.Width, source.Height,
                GraphicsUnit.Pixel,
                attributes
            );
        }

        return enhanced;
    }

    /// <summary>
    /// シャープネス強化 (エッジ強調)
    /// 
    /// 期待効果: 細かい文字の認識率向上
    /// 処理時間: 約 +20-40ms
    /// 
    /// 注意: コントラスト強化と併用推奨
    /// </summary>
    public static Bitmap SharpenEdges(Bitmap source)
    {
        var sharpened = new Bitmap(source.Width, source.Height);

        // シャープニングカーネル (3x3)
        // 中心: 5, 周囲: -1
        float[,] kernel = new float[,]
        {
            { -1, -1, -1 },
            { -1,  9, -1 },
            { -1, -1, -1 }
        };

        using (var g = Graphics.FromImage(sharpened))
        {
            g.DrawImage(source, 0, 0);
        }

        // カーネル畳み込み処理
        for (int y = 1; y < source.Height - 1; y++)
        {
            for (int x = 1; x < source.Width - 1; x++)
            {
                float r = 0, g = 0, b = 0;

                for (int ky = -1; ky <= 1; ky++)
                {
                    for (int kx = -1; kx <= 1; kx++)
                    {
                        var pixel = source.GetPixel(x + kx, y + ky);
                        var weight = kernel[ky + 1, kx + 1];

                        r += pixel.R * weight;
                        g += pixel.G * weight;
                        b += pixel.B * weight;
                    }
                }

                // クランプ: 0-255
                r = Math.Max(0, Math.Min(255, r));
                g = Math.Max(0, Math.Min(255, g));
                b = Math.Max(0, Math.Min(255, b));

                sharpened.SetPixel(x, y, Color.FromArgb((int)r, (int)g, (int)b));
            }
        }

        return sharpened;
    }

    /// <summary>
    /// グレースケール変換
    /// 
    /// 効果: カラー情報ノイズ除去
    /// 処理時間: 約 +10-20ms
    /// 
    /// 適用条件: テキストのみの画像（イラスト・写真なし）
    /// </summary>
    public static Bitmap ToGrayscale(Bitmap source)
    {
        var grayscale = new Bitmap(source.Width, source.Height);

        for (int y = 0; y < source.Height; y++)
        {
            for (int x = 0; x < source.Width; x++)
            {
                var pixel = source.GetPixel(x, y);

                // ITU-R BT.601 輝度計算式
                int gray = (int)(pixel.R * 0.299 + pixel.G * 0.587 + pixel.B * 0.114);

                grayscale.SetPixel(x, y, Color.FromArgb(gray, gray, gray));
            }
        }

        return grayscale;
    }

    /// <summary>
    /// 二値化 (Otsu's Method)
    /// 
    /// 効果: 背景とテキストの明確な分離
    /// 処理時間: 約 +50-100ms
    /// 
    /// ⚠️ 注意: 細い文字が消える可能性あり
    /// 推奨: 太字・大きめのフォントのみ
    /// </summary>
    public static Bitmap Binarize(Bitmap source)
    {
        var grayscale = ToGrayscale(source);
        int threshold = CalculateOtsuThreshold(grayscale);

        var binary = new Bitmap(source.Width, source.Height);

        for (int y = 0; y < grayscale.Height; y++)
        {
            for (int x = 0; x < grayscale.Width; x++)
            {
                var pixel = grayscale.GetPixel(x, y);
                var bw = pixel.R >= threshold ? Color.White : Color.Black;
                binary.SetPixel(x, y, bw);
            }
        }

        return binary;
    }

    /// <summary>
    /// Otsu's Method: 自動閾値計算
    /// 
    /// アルゴリズム: クラス間分散最大化
    /// 参考: https://en.wikipedia.org/wiki/Otsu%27s_method
    /// </summary>
    private static int CalculateOtsuThreshold(Bitmap grayscale)
    {
        // ヒストグラム作成 (0-255)
        int[] histogram = new int[256];
        for (int y = 0; y < grayscale.Height; y++)
        {
            for (int x = 0; x < grayscale.Width; x++)
            {
                histogram[grayscale.GetPixel(x, y).R]++;
            }
        }

        // Otsu's Method実装
        int total = grayscale.Width * grayscale.Height;
        double sum = 0;
        for (int i = 0; i < 256; i++)
        {
            sum += i * histogram[i];
        }

        double sumB = 0;
        int wB = 0;
        int wF = 0;
        double maxVariance = 0;
        int threshold = 0;

        for (int i = 0; i < 256; i++)
        {
            wB += histogram[i];
            if (wB == 0) continue;

            wF = total - wB;
            if (wF == 0) break;

            sumB += i * histogram[i];
            double mB = sumB / wB;
            double mF = (sum - sumB) / wF;

            // クラス間分散
            double variance = wB * wF * (mB - mF) * (mB - mF);

            if (variance > maxVariance)
            {
                maxVariance = variance;
                threshold = i;
            }
        }

        return threshold;
    }

    /// <summary>
    /// 推奨前処理パイプライン
    /// 
    /// 適用順序:
    /// 1. コントラスト強化 (必須)
    /// 2. シャープニング (オプション)
    /// 
    /// 期待効果: 識字率 93% → 95%+
    /// 処理時間: 約 +50-90ms
    /// </summary>
    /// <param name="source">元画像</param>
    /// <param name="applySharpen">シャープニング適用 (デフォルト: false)</param>
    /// <returns>前処理済み画像</returns>
    public static Bitmap ApplyRecommendedPreprocessing(Bitmap source, bool applySharpen = false)
    {
        // Step 1: コントラスト強化 (最重要)
        var enhanced = EnhanceContrast(source);

        // Step 2: シャープニング (オプション)
        if (applySharpen)
        {
            var sharpened = SharpenEdges(enhanced);
            enhanced.Dispose();
            return sharpened;
        }

        return enhanced;
    }
}
