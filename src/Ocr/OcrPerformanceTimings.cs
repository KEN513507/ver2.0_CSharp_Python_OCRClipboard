using System;

namespace Ocr;

/// <summary>
/// OCR パイプライン各ステージの計測値を保持するためのレコード。
/// </summary>
public sealed record OcrPerformanceTimings(TimeSpan Preprocess, TimeSpan Inference, TimeSpan Postprocess)
{
    public double PreprocessMilliseconds => Preprocess.TotalMilliseconds;
    public double InferenceMilliseconds => Inference.TotalMilliseconds;
    public double PostprocessMilliseconds => Postprocess.TotalMilliseconds;
}
