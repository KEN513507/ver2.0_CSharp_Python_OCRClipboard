using System.Diagnostics;
using System.Text;

namespace OCRClipboard.App.Ipc;

public sealed class PythonProcessHost : IDisposable
{
    private readonly string _pythonExe;
    private readonly string _module;
    private readonly string _workingDirectory;
    private Process? _proc;
    private CancellationTokenSource? _readCts;

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

        var start = new ProcessStartInfo
        {
            FileName = _pythonExe,
            Arguments = $"-u -X utf8 -m {_module}",
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
            WorkingDirectory = _workingDirectory,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
        };

        // Python UTF-8 enforcement
        start.Environment["PYTHONIOENCODING"] = "utf-8";
        start.Environment["PYTHONUTF8"] = "1";
        start.Environment["PYTHONLEGACYWINDOWSSTDIO"] = "0";

        // Ensure Python can find src/python
        var pythonPath = Path.Combine(_workingDirectory, "src", "python");
        if (Directory.Exists(pythonPath))
        {
            if (start.Environment.ContainsKey("PYTHONPATH"))
                start.Environment["PYTHONPATH"] = start.Environment["PYTHONPATH"] + Path.PathSeparator + pythonPath;
            else
                start.Environment["PYTHONPATH"] = pythonPath;
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

    public Task WriteLineAsync(string line)
    {
        if (_proc?.StandardInput == null) throw new InvalidOperationException("Python not started");
        _proc.StandardInput.WriteLine(line);
        _proc.StandardInput.Flush();
        return Task.CompletedTask;
    }

    public void Dispose()
    {
        _ = StopAsync();
    }
}
