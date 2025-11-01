using System;
using System.Drawing;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Infra;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Ocr;
using Quality;

namespace Worker;

/// <summary>
/// stdin/stdout を使う OCR ワーカーの概略実装。Python 版の ocr_worker/main.py に相当。
/// </summary>
public sealed class Worker
{
    private readonly IOcrEngine _engine;
    private readonly IWorkerEmitter _emitter;
    private readonly ILogger _logger;
    private readonly QualityConfig _config;

    public Worker(
        IOcrEngine engine,
        IWorkerEmitter emitter,
        ILogger? logger = null,
        QualityConfig? config = null)
    {
        _engine = engine;
        _emitter = emitter;
        _logger = logger ?? NullLogger.Instance;
        _config = config ?? new QualityConfig();
    }

    public async Task RunAsync(CancellationToken cancellationToken)
    {
        string? line;
        while (!cancellationToken.IsCancellationRequested && (line = await Console.In.ReadLineAsync()) is not null)
        {
            line = line.Trim();
            if (string.IsNullOrEmpty(line))
                continue;

            try
            {
                var request = JsonSerializer.Deserialize<OcrRequest>(line);
                if (request?.ImagePath is null)
                {
                    EmitErrorResponse("image_path required");
                    continue;
                }

                using var bitmap = new Bitmap(request.ImagePath);
                using (PerfLogger.MeasureCapture(_logger))
                {
                    // capture の時間計測用のダミーブロック (実際はすでに Bitmap がある想定)
                }

                OcrResult result;
                using (PerfLogger.MeasureInference(_logger))
                    result = await _engine.RecognizeAsync(bitmap, cancellationToken);

                PerfLogger.LogOcrSummary(_logger, result.FragmentCount, result.MeanConfidence, result.MinConfidence);

                var combinedText = result.CombinedText;
                var qualityOk = result.FragmentCount == 0
                    ? false
                    : combinedText.Length >= _config.MinConfLength && result.MeanConfidence >= _config.MinConfidence;

                var response = new
                {
                    success = true,
                    text = combinedText,
                    quality_ok = qualityOk,
                };
                EmitSuccess(JsonSerializer.Serialize(response));
            }
            catch (JsonException ex)
            {
                _logger.LogWarning("Invalid JSON received: {Message}", ex.Message);
                EmitErrorResponse(ex.Message);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to process line");
                EmitErrorResponse(ex.Message);
            }
        }
    }

    private void EmitSuccess(string json) => _emitter.EmitSuccess(json);
    private void EmitError(string json) => _emitter.EmitError(json);
    private void EmitErrorResponse(string error)
    {
        var response = new
        {
            success = false,
            error
        };
        EmitError(JsonSerializer.Serialize(response));
    }

    private sealed record OcrRequest(string? ImagePath);
}
