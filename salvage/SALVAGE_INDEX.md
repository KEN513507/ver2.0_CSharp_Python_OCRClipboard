# Salvage Index

| カテゴリ | ファイル/ディレクトリ | 説明 |
|----------|-----------------------|------|
| テスト | `tests/conftest.py` | autouse モック (tkinter/mss/OCR) の C# 移植参考用 Python 版。 |
|         | `tests/test_quality_config.py` | QualityConfig を環境変数で切り替えるテストパターン。 |
|         | `tests/test_worker_main.py` | stdin JSON ハンドリングの検証例。 |
| 品質 | `python/quality_config.py` | QualityConfig + normalize_text の原典。 |
| ログ | `notes/perf_logging.md` | `[PERF]` / `[OCR]` ログの書式。 |
| キャプチャ | `capture/mss_threading_pattern.md` | mss での with 使い捨て + フォールバック設計。 |
| Slow 分離 | `tests/slow_test_pattern.md` | pytest slow → xUnit Category 変換メモ。 |

C# 版は以下のディレクトリで再構成済み：
- `src/Infra/PerfLogger.cs`
- `src/Quality/QualityConfig.cs`
- `src/Quality/OcrQualityEvaluator.cs`
- `src/Ocr/FakeOcrEngine.cs`
- `tests/Common/*.cs`, `tests/Quality/*.cs`, `tests/Ocr/*.cs`
