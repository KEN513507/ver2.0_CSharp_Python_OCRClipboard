using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

namespace Quality;

/// <summary>
/// Python の judge_quality ロジックを C# で再現。
/// </summary>
public static class OcrQualityEvaluator
{
    public static bool IsAcceptable(string expected, string actual, double confidence, QualityConfig config)
    {
        var normalizedExpected = Normalize(expected, config);
        var normalizedActual = Normalize(actual, config);

        var minLength = Math.Max(1, (int)(normalizedExpected.Length * config.MinLengthRatio));
        if (normalizedActual.Length < minLength) return false;

        var alphaRatio = normalizedActual.Count(char.IsLetterOrDigit) / (double)Math.Max(1, normalizedActual.Length);
        if (alphaRatio < config.MinAlphaRatio) return false;

        if (normalizedActual.Length >= config.MinConfLength && confidence < config.MinConfidence)
            return false;

        var distance = LevenshteinDistance(normalizedExpected, normalizedActual);
        var cap = Math.Min(config.MaxAbsEdit, (int)(normalizedExpected.Length * config.MaxRelEdit));
        var threshold = Math.Max(config.BaseErrorFloor, cap);
        return distance <= threshold;
    }

    private static string Normalize(string text, QualityConfig config)
    {
        if (string.IsNullOrWhiteSpace(text)) return string.Empty;
        var normalized = config.NormalizeNfkc
            ? text.Normalize(NormalizationForm.FormKC)
            : text;
        if (config.IgnoreCase)
            normalized = normalized.ToLower(CultureInfo.InvariantCulture);
        normalized = Regex.Replace(normalized, @"\s+", " ");
        return normalized.Trim();
    }

    private static int LevenshteinDistance(string s, string t)
    {
        if (s.Length == 0) return t.Length;
        if (t.Length == 0) return s.Length;

        var previous = new int[t.Length + 1];
        var current = new int[t.Length + 1];

        for (var j = 0; j <= t.Length; j++)
            previous[j] = j;

        for (var i = 1; i <= s.Length; i++)
        {
            current[0] = i;
            for (var j = 1; j <= t.Length; j++)
            {
                var cost = s[i - 1] == t[j - 1] ? 0 : 1;
                current[j] = Math.Min(
                    Math.Min(current[j - 1] + 1, previous[j] + 1),
                    previous[j - 1] + cost);
            }

            Array.Copy(current, previous, current.Length);
        }

        return current[t.Length];
    }
}
