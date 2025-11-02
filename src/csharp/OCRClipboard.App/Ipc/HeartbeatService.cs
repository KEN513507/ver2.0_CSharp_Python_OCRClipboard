using System.Threading;
using System.Threading.Tasks;
using OCRClipboard.App.Dto;

namespace OCRClipboard.App.Ipc;

public sealed class HeartbeatService : IAsyncDisposable
{
    private readonly JsonRpcClient _client;
    private readonly TimeSpan _interval;
    private readonly TimeSpan _timeout;
    private CancellationTokenSource? _cts;
    private Task? _loop;
    private int _consecutiveFailures;
    private string _lastMessage = string.Empty;

    public WorkerStatus Status { get; private set; } = WorkerStatus.Starting;
    public event Action<WorkerStatus, string>? OnStatusChanged;

    public HeartbeatService(JsonRpcClient client, TimeSpan? interval = null, TimeSpan? timeout = null)
    {
        _client = client ?? throw new ArgumentNullException(nameof(client));
        _interval = interval ?? TimeSpan.FromSeconds(5);
        _timeout = timeout ?? TimeSpan.FromMilliseconds(1500);
    }

    public void Start()
    {
        if (_loop != null)
        {
            return;
        }

        _cts = new CancellationTokenSource();
        _loop = Task.Run(() => RunAsync(_cts.Token));
    }

    private async Task RunAsync(CancellationToken token)
    {
        try
        {
            await SendPingAsync(token).ConfigureAwait(false);

            using var timer = new PeriodicTimer(_interval);
            while (await timer.WaitForNextTickAsync(token).ConfigureAwait(false))
            {
                await SendPingAsync(token).ConfigureAwait(false);
            }
        }
        catch (OperationCanceledException) when (token.IsCancellationRequested)
        {
            // graceful shutdown
        }
    }

    private async Task SendPingAsync(CancellationToken token)
    {
        var ts = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        try
        {
            using var linkedCts = CancellationTokenSource.CreateLinkedTokenSource(token);
            linkedCts.CancelAfter(_timeout);

            var pong = await _client.CallAsync<PongResponse>(
                type: "ping",
                payload: new { ts },
                linkedCts.Token).ConfigureAwait(false);

            if (pong?.Ok == true)
            {
                _consecutiveFailures = 0;
                var warmed = pong.WarmedLangs is { Length: > 0 }
                    ? string.Join(",", pong.WarmedLangs)
                    : "-";
                UpdateStatus(
                    WorkerStatus.Healthy,
                    $"pid={pong.Pid} ver={pong.Version ?? "unknown"} warmed={warmed}"
                );
            }
            else
            {
                HandleFailure(pong?.Error ?? "pong not ok");
            }
        }
        catch (OperationCanceledException) when (!token.IsCancellationRequested)
        {
            HandleFailure("timeout");
        }
        catch (Exception ex)
        {
            HandleFailure(ex.Message);
        }
    }

    private void HandleFailure(string message)
    {
        _consecutiveFailures++;
        var status = _consecutiveFailures >= 3 ? WorkerStatus.Unreachable : WorkerStatus.Degraded;
        UpdateStatus(status, message);
    }

    private void UpdateStatus(WorkerStatus status, string message)
    {
        if (Status != status || !string.Equals(_lastMessage, message, StringComparison.Ordinal))
        {
            OnStatusChanged?.Invoke(status, message);
            Status = status;
            _lastMessage = message;
        }
    }

    public async ValueTask DisposeAsync()
    {
        if (_cts == null)
        {
            return;
        }

        _cts.Cancel();
        try
        {
            if (_loop != null)
            {
                await _loop.ConfigureAwait(false);
            }
        }
        catch (OperationCanceledException)
        {
            // ignore cancellation during shutdown
        }
        finally
        {
            _cts.Dispose();
            _cts = null;
            _loop = null;
        }
    }
}
