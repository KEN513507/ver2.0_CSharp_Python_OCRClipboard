using Quality;
using Tests.Common;
using Xunit;

namespace Tests.Quality;

public sealed class QualityEvaluatorTests : IClassFixture<ConfigOverrideFixture>
{
    private readonly ConfigOverrideFixture _fixture;

    public QualityEvaluatorTests(ConfigOverrideFixture fixture) => _fixture = fixture;

    [Fact]
    public void NfkcAndIgnoreCase_EnableAndDisable()
    {
        var config = new QualityConfig
        {
            NormalizeNfkc = true,
            IgnoreCase = true,
            BaseErrorFloor = 0,
            MaxAbsEdit = 0,
            MaxRelEdit = 0,
            MinConfLength = 0,
            MinConfidence = 0,
        };

        Assert.True(OcrQualityEvaluator.IsAcceptable("ＡＢＣ", "abc", 0.0, config));
        Assert.True(OcrQualityEvaluator.IsAcceptable("Hello", "hello", 0.0, config));

        config = config with { NormalizeNfkc = false, IgnoreCase = false };
        Assert.False(OcrQualityEvaluator.IsAcceptable("ＡＢＣ", "abc", 0.0, config));
        Assert.False(OcrQualityEvaluator.IsAcceptable("Hello", "hello", 0.0, config));
    }

    [Fact]
    public void EnvironmentOverridesAreApplied()
    {
        _fixture.WithEnv("OCR_MIN_CONFIDENCE", "0.5")
                .WithEnv("OCR_MAX_ABS_EDIT", "5")
                .WithEnv("OCR_MAX_REL_EDIT", "0.1");

        var config = new QualityConfig();
        Assert.Equal(0.5, config.MinConfidence);
        Assert.Equal(5, config.MaxAbsEdit);
        Assert.Equal(0.1, config.MaxRelEdit);
    }
}
