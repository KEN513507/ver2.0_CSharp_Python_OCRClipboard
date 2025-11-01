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
            Arguments = $"-u -m {_module}",
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
            WorkingDirectory = _workingDirectory,
        };

        // Ensure Python can find src/python and ocr-screenshot-app
        var paths = new List<string>
        {
            ".",  // Repository root
            Path.Combine(_workingDirectory, "src", "python"),
            Path.Combine(_workingDirectory, "ocr-screenshot-app")
        };

        var validPaths = paths.Where(Directory.Exists).ToList();
        if (validPaths.Any())
        {
            var pythonPathValue = string.Join(Path.PathSeparator.ToString(), validPaths);
            if (start.Environment.ContainsKey("PYTHONPATH"))
                start.Environment["PYTHONPATH"] = pythonPathValue + Path.PathSeparator + start.Environment["PYTHONPATH"];
            else
                start.Environment["PYTHONPATH"] = pythonPathValue;
        }

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

