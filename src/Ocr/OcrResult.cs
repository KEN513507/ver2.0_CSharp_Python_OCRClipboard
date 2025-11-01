using System;
using System.Collections.Generic;
using System.Linq;

namespace Ocr;

public sealed record OcrResult(
    IReadOnlyList<OcrFragment> Fragments,
    TimeSpan Elapsed,
    OcrPerformanceTimings? Timings = null)
{
    public int FragmentCount => Fragments.Count;
    public double MeanConfidence => Fragments.Count == 0 ? 0.0 : Fragments.Average(f => f.Confidence);
    public double MinConfidence => Fragments.Count == 0 ? 0.0 : Fragments.Min(f => f.Confidence);
    public string CombinedText => string.Concat(Fragments.Select(f => f.Text));
}
