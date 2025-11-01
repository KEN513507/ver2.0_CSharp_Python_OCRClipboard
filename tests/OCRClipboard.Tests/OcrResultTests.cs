using System;
using System.Collections.Generic;
using System.Drawing;
using Ocr;
using Xunit;

namespace OCRClipboard.Tests;

public sealed class OcrResultTests
{
    [Fact]
    public void CombinedText_ConcatenatesFragments()
    {
        var fragments = new List<OcrFragment>
        {
            new("テスト", 0.9, Rectangle.Empty),
            new("中", 0.8, Rectangle.Empty),
            new("心", 0.7, Rectangle.Empty),
        };

        var result = new OcrResult(fragments, TimeSpan.FromMilliseconds(5));

        Assert.Equal("テスト中心", result.CombinedText);
        Assert.Equal(3, result.FragmentCount);
        Assert.Equal(0.8, result.MeanConfidence, 2);
        Assert.Equal(0.7, result.MinConfidence, 2);
    }
}
