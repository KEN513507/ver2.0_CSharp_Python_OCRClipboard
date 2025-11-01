using System;

namespace Quality;

/// <summary>
/// OCR の品質閾値を管理する設定クラス。
/// Python 版の QualityConfig を C# に移植したもの。
/// すべての値は環境変数で上書き可能。
/// </summary>
public sealed record QualityConfig
{
    public int MaxAbsEdit { get; init; } = EnvInt("OCR_MAX_ABS_EDIT", 20);
    public double MaxRelEdit { get; init; } = EnvDouble("OCR_MAX_REL_EDIT", 0.25);
    public int BaseErrorFloor { get; init; } = EnvInt("OCR_BASE_ERROR_FLOOR", 5);
    public double MinConfidence { get; init; } = EnvDouble("OCR_MIN_CONFIDENCE", 0.70);

    public int MinConfLength { get; init; } = EnvInt("OCR_MIN_CONF_LENGTH", 5);
    public double MinAlphaRatio { get; init; } = EnvDouble("OCR_MIN_ALPHA_RATIO", 0.5);
    public double MinLengthRatio { get; init; } = EnvDouble("OCR_MIN_LENGTH_RATIO", 0.25);

    public bool NormalizeNfkc { get; init; } = EnvBool("OCR_NORMALIZE_NFKC", true);
    public bool IgnoreCase { get; init; } = EnvBool("OCR_IGNORE_CASE", true);

    private static bool EnvBool(string name, bool defaultValue)
    {
        var value = Environment.GetEnvironmentVariable(name);
        if (value is null) return defaultValue;
        return value.Trim().ToLowerInvariant() is "1" or "true" or "yes" or "on";
    }

    private static int EnvInt(string name, int defaultValue)
    {
        var value = Environment.GetEnvironmentVariable(name);
        if (value is null) return defaultValue;
        return int.TryParse(value, out var parsed) ? parsed : defaultValue;
    }

    private static double EnvDouble(string name, double defaultValue)
    {
        var value = Environment.GetEnvironmentVariable(name);
        if (value is null) return defaultValue;
        return double.TryParse(value, out var parsed) ? parsed : defaultValue;
    }
}
