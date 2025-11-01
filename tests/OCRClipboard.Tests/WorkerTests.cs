using System;
using System.Drawing;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Ocr;
using Worker;
using Xunit;

namespace OCRClipboard.Tests;

public sealed class WorkerTests
{
    [Fact]
    public async Task InvalidJsonAndValidRequest_AreReportedSeparately()
    {
        var tempImage = Path.GetTempFileName();
        using (var bmp = new Bitmap(10, 10))
        {
            using var g = Graphics.FromImage(bmp);
            g.Clear(Color.White);
            bmp.Save(tempImage);
        }

        var originalIn = Console.In;
        var originalOut = Console.Out;

        try
        {
            var payload = "\nnot json\n" +
                          $"{{\"image_path\":\"{tempImage.Replace("\\", "\\\\")}\"}}\n";

            using var stdin = new StringReader(payload);
            using var stdout = new StringWriter(new StringBuilder());
            Console.SetIn(stdin);
            Console.SetOut(stdout);

            var worker = new Worker.Worker(new FakeOcrEngine(), new ConsoleEmitter());
            await worker.RunAsync(CancellationToken.None);

            var output = stdout.ToString().Split(Environment.NewLine, StringSplitOptions.RemoveEmptyEntries);
            Assert.Contains(output, l => l.Contains("\"success\":false"));
            Assert.Contains(output, l => l.Contains("\"success\":true"));
        }
        finally
        {
            Console.SetIn(originalIn);
            Console.SetOut(originalOut);
            File.Delete(tempImage);
        }
    }

    private sealed class ConsoleEmitter : IWorkerEmitter
    {
        public void EmitSuccess(string json) => Console.Out.WriteLine(json);
        public void EmitError(string json) => Console.Out.WriteLine(json);
    }
}
