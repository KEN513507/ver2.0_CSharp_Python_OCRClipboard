# Slow テスト分離パターン (pytest -> xUnit)

| Python (`@pytest.mark.slow`) | C# (xUnit)  |
|-----------------------------|-------------|
| `pytest -m "not slow"`       | `dotnet test --filter Category!=SlowOCR` |
| autouse fixture で依存をモック | `FakeOcrEngine` + `SlowOcrAttribute` |

```csharp
[SlowOcr]
public class WindowsMediaOcrIntegrationTests
{
    [Fact]
    public async Task RunRealOcr()
    {
        // 実機向けの Windows.Media.Ocr 呼び出し（TODO: 実装）
    }
}
```

- 通常のテストは `SlowOcrAttribute` を付けず FakeOcrEngine を使用。  
- 実機テストだけ `WindowsMediaOcrEngine` を new して差し替える。  
- CI では `--filter Category!=SlowOCR` でスキップ、必要なときのみフル実行。
