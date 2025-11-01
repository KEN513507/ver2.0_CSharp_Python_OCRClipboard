# pytest slow マーク分離パターン

## 目的
重量テスト（実OCR、ネットワーク、大量データ）を**デフォルトから除外**し、CI/開発速度を確保。

## 実装

### 1. `pyproject.toml`
```toml
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]
addopts = "-q -m 'not slow'"  # デフォルトで slow を除外
```

### 2. `conftest.py` でモック自動適用
```python
import pytest

@pytest.fixture(scope="session", autouse=True)
def _mock_paddleocr(request):
    """非slowテストではPaddleOCRをモック化（高速化）"""
    if "slow" in request.keywords:
        yield  # slowテストは実エンジン使用
    else:
        with patch("ocr_screenshot_app.ocr.PaddleOCR") as mock:
            mock.return_value.ocr.return_value = [
                [[[0, 0], [100, 0], [100, 50], [0, 50]], ("モックテキスト", 0.95)]
            ]
            yield mock
```

### 3. テストファイル
```python
import pytest

def test_fast_logic():
    """常に実行される高速テスト（モック使用）"""
    result = some_function()
    assert result == expected

@pytest.mark.slow
def test_real_ocr():
    """slowマーク: 明示的に実行時のみ動く（実エンジン）"""
    real_result = real_ocr_engine.recognize(image)
    assert real_result.confidence > 0.7
```

## 実行方法
```bash
pytest                        # デフォルト: slow除外（高速）
pytest -m "not slow"          # 明示的に除外
pytest -m "slow"              # slowのみ実行
pytest -m "slow or not slow"  # 全件実行
```

## 適用メリット
- CI実行時間を**90%以上削減**（実機OCR 90秒→モック 0.1秒）
- ローカル開発で**即座にフィードバック**
- リリース前に `-m slow` で最終検証

## 他言語への移植
- C# xUnit: `[Trait("Category", "Slow")]` + `dotnet test --filter "Category!=Slow"`
- TypeScript Jest: `describe.skip` or custom test runner filters
