using System.Diagnostics;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace OCRClipboard.App.Ipc;

public sealed class PythonProcessHost : IDisposable
{
    private readonly string _pythonExe;
    private readonly string _module;
    private readonly string _workingDirectory;
    private Process? _proc;
    private CancellationTokenSource? _readCts;
    private readonly SemaphoreSlim _writeLock = new(1, 1);

    public event Action<string>? OnLineReceived;

    public PythonProcessHost(string pythonExe, string module, string workingDirectory)
    {
        _pythonExe = pythonExe;
        _module = module;
        _workingDirectory = workingDirectory;
    }

    public async Task StartAsync()
    {
        if (_proc != null) return;

        var repoRoot = _workingDirectory;
        var pythonSrcDir = Path.Combine(repoRoot, "src", "python");
        if (!Directory.Exists(pythonSrcDir))
        {
            pythonSrcDir = repoRoot;
        }

        var start = new ProcessStartInfo
        {
            FileName = _pythonExe,
            Arguments = $"-u -X utf8 -m {_module} --stdio",
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
            WorkingDirectory = pythonSrcDir,
            StandardOutputEncoding = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false),
            StandardErrorEncoding = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false),
        };

        // Python UTF-8 enforcement
        start.Environment["PYTHONIOENCODING"] = "utf-8";
        start.Environment["PYTHONUTF8"] = "1";
        start.Environment["PYTHONLEGACYWINDOWSSTDIO"] = "0";

        // Ensure Python can find src/python
        if (Directory.Exists(pythonSrcDir))
        {
            var existingPyPath = start.Environment.ContainsKey("PYTHONPATH")
                ? start.Environment["PYTHONPATH"]
                : string.Empty;
            start.Environment["PYTHONPATH"] = string.IsNullOrWhiteSpace(existingPyPath)
                ? pythonSrcDir
                : pythonSrcDir + Path.PathSeparator + existingPyPath;
        }

        // Silence Python logging noise
        start.Environment["PADDLEOCR_SHOW_LOG"] = "False";
        start.Environment["FLAGS_minloglevel"] = "3";
        start.Environment["GLOG_minloglevel"] = "3";
        start.Environment["TQDM_DISABLE"] = "1";
        start.Environment["PDX_NO_TQDM"] = "1";
        start.Environment["PDX_OFFLINE"] = "1";

        // OCR performance optimization: force mobile models
        start.Environment["OCR_DOC_PIPELINE"] = Environment.GetEnvironmentVariable("OCR_DOC_PIPELINE") ?? "off";
        start.Environment["OCR_PADDLE_VARIANT"] = Environment.GetEnvironmentVariable("OCR_PADDLE_VARIANT") ?? "mobile";
        start.Environment["OCR_PADDLE_USE_CLS"] = Environment.GetEnvironmentVariable("OCR_PADDLE_USE_CLS") ?? "0";
        start.Environment["OCR_PADDLE_LANG"] = Environment.GetEnvironmentVariable("OCR_PADDLE_LANG") ?? "japan";
        start.Environment["OCR_PADDLE_WARMUP_LANGS"] = Environment.GetEnvironmentVariable("OCR_PADDLE_WARMUP_LANGS") ?? "japan,en";

        _proc = new Process { StartInfo = start, EnableRaisingEvents = true };
        _proc.ErrorDataReceived += (_, e) => { if (!string.IsNullOrEmpty(e.Data)) Console.Error.WriteLine($"[pyerr] {e.Data}"); };
        if (!_proc.Start()) throw new InvalidOperationException("Failed to start Python process.");
        _proc.BeginErrorReadLine();

        _readCts = new CancellationTokenSource();
        _ = Task.Run(() => ReadLoopAsync(_readCts.Token));

        await Task.CompletedTask;
    }

    public async Task StopAsync()
    {
        try
        {
            _readCts?.Cancel();
            if (_proc?.HasExited == false)
            {
                _proc.Kill(entireProcessTree: true);
            }
        }
        catch { /* ignore */ }
        finally
        {
            _proc?.Dispose();
            _proc = null;
            _readCts?.Dispose();
            _readCts = null;
        }
        await Task.CompletedTask;
    }

    private async Task ReadLoopAsync(CancellationToken ct)
    {
        if (_proc?.StandardOutput == null) return;
        var reader = _proc.StandardOutput;
        while (!ct.IsCancellationRequested && !_proc.HasExited)
        {
            var line = await reader.ReadLineAsync();
            if (line == null) break;
            OnLineReceived?.Invoke(line);
        }
    }

    public async Task WriteLineAsync(string line)
    {
        if (_proc?.StandardInput == null) throw new InvalidOperationException("Python not started");
        await _writeLock.WaitAsync().ConfigureAwait(false);
        try
        {
            await _proc.StandardInput.WriteLineAsync(line).ConfigureAwait(false);
            await _proc.StandardInput.FlushAsync().ConfigureAwait(false);
        }
        finally
        {
            _writeLock.Release();
        }
    }

    public void Dispose()
    {
        _ = StopAsync();
        _writeLock.Dispose();
    }
}
