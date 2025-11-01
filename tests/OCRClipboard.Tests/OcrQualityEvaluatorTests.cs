using Quality;
using Tests.Common;
using Xunit;

namespace OCRClipboard.Tests;

public sealed class OcrQualityEvaluatorTests
{
    [Fact]
    public void AcceptsTextWithinThreshold()
    {
        var config = new QualityConfig();
        var ok = OcrQualityEvaluator.IsAcceptable(
            expected: "Geminiへのプロンプトを入力",
            actual: "geminiへのプロンプトを入力 ",
            confidence: 0.95,
            config);

        Assert.True(ok);
    }

    [Fact]
    public void RejectsLowConfidenceWhenLengthRequirementMet()
    {
        using var fixture = new ConfigOverrideFixture()
            .WithEnv("OCR_MIN_CONFIDENCE", "0.9");

        var config = new QualityConfig();
        var ok = OcrQualityEvaluator.IsAcceptable(
            expected: "テストケース",
            actual: "テストケース",
            confidence: 0.3,
            config);

        Assert.False(ok);
    }

    [Fact]
    public void EnvironmentOverridesAreApplied()
    {
        using var fixture = new ConfigOverrideFixture()
            .WithEnv("OCR_MIN_CONFIDENCE", "0.5")
            .WithEnv("OCR_MAX_ABS_EDIT", "5")
            .WithEnv("OCR_MAX_REL_EDIT", "0.1");

        var config = new QualityConfig();
        Assert.Equal(0.5, config.MinConfidence);
        Assert.Equal(5, config.MaxAbsEdit);
        Assert.Equal(0.1, config.MaxRelEdit);
    }
}
