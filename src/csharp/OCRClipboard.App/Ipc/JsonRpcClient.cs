using System.Collections.Concurrent;
using System.Text.Json;
using System.Text.Json.Serialization;
using OCRClipboard.App.Dto;

namespace OCRClipboard.App.Ipc;

public sealed class JsonRpcClient
{
    private readonly PythonProcessHost _host;
    private readonly ConcurrentDictionary<string, TaskCompletionSource<JsonElement>> _pending = new();
    private readonly JsonSerializerOptions _jsonOpts = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        WriteIndented = false
    };
    private static readonly char[] StripLeading = new[] { '\uFEFF', '\u200B', '\u2060' };

    public JsonRpcClient(PythonProcessHost host)
    {
        _host = host;
        _host.OnLineReceived += HandleLine;
    }

    private void HandleLine(string line)
    {
        if (string.IsNullOrWhiteSpace(line)) return;

        // Strip BOM and zero-width characters
        line = line.Trim().TrimStart(StripLeading);
        if (line.Length == 0) return;

        // JSON must start with {
        char c0 = line[0];
        if (c0 != '{')
        {
#if DEBUG
            var preview = line.Length > 120 ? line[..120] + "…" : line;
            Console.Error.WriteLine($"[py-raw drop] {preview}");
#endif
            return;
        }

        try
        {
#if DEBUG
            Console.Error.WriteLine($"[py-json] {(line.Length > 200 ? line[..200] + "…" : line)}");
#endif
            var env = JsonSerializer.Deserialize<Envelope>(line, _jsonOpts);
            if (env == null || string.IsNullOrWhiteSpace(env.Id))
            {
#if DEBUG
                Console.Error.WriteLine($"[py-json drop] Missing 'id' field");
#endif
                return;
            }

            if (_pending.TryRemove(env.Id, out var tcs))
            {
                tcs.TrySetResult(env.Payload);
            }
        }
        catch (Exception ex)
        {
            var preview = line.Length > 200 ? line[..200] + "…" : line;
            Console.Error.WriteLine($"[C#] Failed to handle line: {ex.Message} | raw={preview}");
        }
    }

    public async Task<T?> CallAsync<T>(string type, object payload, CancellationToken ct)
    {
        var id = Guid.NewGuid().ToString();
        var tcs = new TaskCompletionSource<JsonElement>(TaskCreationOptions.RunContinuationsAsynchronously);
        _pending[id] = tcs;

        var env = new
        {
            id,
            type,
            payload
        };

        var line = JsonSerializer.Serialize(env, _jsonOpts);
        await _host.WriteLineAsync(line).ConfigureAwait(false);

        using var reg = ct.Register(() =>
        {
            if (_pending.TryRemove(id, out var t))
            {
                t.TrySetCanceled(ct);
            }
        });

        var json = await tcs.Task.ConfigureAwait(false);
        try
        {
            return JsonSerializer.Deserialize<T>(json.GetRawText(), _jsonOpts);
        }
        catch
        {
            return default;
        }
    }
}
