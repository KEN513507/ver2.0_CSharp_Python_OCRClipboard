using System;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Ocr;
using Tests.Common;
using Worker;
using Xunit;

namespace Tests.Ocr;

public sealed class WorkerTests
{
    [Fact]
    public async Task InvalidJsonAndValidRequest_AreReportedSeparately()
    {
        using var stdin = new StringReader("\nnot json\n{\"image_path\":\"dummy.png\"}\n");
        using var stdout = new StringWriter(new StringBuilder());
        Console.SetIn(stdin);
        Console.SetOut(stdout);

        var worker = new Worker(new FakeOcrEngine(), new ConsoleEmitter());
        await worker.RunAsync(CancellationToken.None);

        var lines = stdout.ToString().Split(Environment.NewLine, StringSplitOptions.RemoveEmptyEntries);
        Assert.Contains(lines, l => l.Contains("\"success\":false"));
        Assert.Contains(lines, l => l.Contains("\"success\":true"));
    }

    private sealed class ConsoleEmitter : IWorkerEmitter
    {
        public void EmitSuccess(string json) => Console.Out.WriteLine(json);
        public void EmitError(string json) => Console.Out.WriteLine(json);
    }
}
