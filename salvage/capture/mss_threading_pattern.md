# Capture 失敗に備えたパターン（Python mss -> C#）

1. キャプチャハンドルは毎回 `using` で生成して使い捨て。  
2. 例外が発生したら 50ms 待って再試行。  
3. それでも駄目なら `Graphics.CopyFromScreen` のフォールバックを使い、ログに警告を残す。  
4. アプリ起動時に `SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)` を呼んで DPI ズレを抑制。

```csharp
public static Bitmap Capture(Rectangle rect)
{
    try
    {
        return CaptureOnce(rect);
    }
    catch (Exception ex)
    {
        Log.Warning(ex, "Primary capture failed, retry 50ms later");
        Thread.Sleep(50);
        return CaptureOnce(rect);
    }
}

private static Bitmap CaptureOnce(Rectangle rect)
{
    using var bmp = new Bitmap(rect.Width, rect.Height);
    using var g = Graphics.FromImage(bmp);
    g.CopyFromScreen(rect.Location, Point.Empty, rect.Size);
    return (Bitmap)bmp.Clone();
}
```
