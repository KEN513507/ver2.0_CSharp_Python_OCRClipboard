using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Infra;

/// <summary>
/// [PERF]/[OCR] ログを出力するユーティリティ。
/// Python 版の salvage/notes/perf_logging.md を C# に移植したもの。
/// </summary>
public static class PerfLogger
{
    public static IDisposable MeasureCapture(ILogger logger) =>
        new PerfScope(logger, "capture");

    public static IDisposable MeasurePreprocess(ILogger logger) =>
        new PerfScope(logger, "preproc");

    public static IDisposable MeasureInference(ILogger logger) =>
        new PerfScope(logger, "infer");

    public static IDisposable MeasurePostprocess(ILogger logger) =>
        new PerfScope(logger, "postproc");

    public static void LogOcrSummary(
        ILogger logger,
        int fragmentCount,
        double meanConfidence,
        double minConfidence)
    {
        logger.LogInformation(
            "[OCR] n_fragments={FragmentCount} mean_conf={Mean:F2} min_conf={Min:F2}",
            fragmentCount,
            meanConfidence,
            minConfidence);
    }

    private sealed class PerfScope : IDisposable
    {
        private readonly ILogger _logger;
        private readonly string _stage;
        private readonly Stopwatch _stopwatch;

        public PerfScope(ILogger logger, string stage)
        {
            _logger = logger;
            _stage = stage;
            _stopwatch = Stopwatch.StartNew();
        }

        public void Dispose()
        {
            _stopwatch.Stop();
            _logger.LogInformation("[PERF] {Stage}={Elapsed}ms", _stage, _stopwatch.Elapsed.TotalMilliseconds);
        }
    }
}
