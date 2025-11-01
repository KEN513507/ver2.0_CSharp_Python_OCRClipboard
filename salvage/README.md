# Salvaged OCR Utilities

アーカイブ前に「次の OCR 開発でも再利用できる」部品だけをここにまとめています。  
フォルダ構成と主な用途は下記の通りです。

| パス | 内容 / 使い道 |
|------|---------------|
| `tests/conftest.py` | 重い OCR 依存を autouse フィクスチャでモック化する仕組み（`slow` マーカーは実機を許可）。 |
| `tests/test_quality_config.py` | `QualityConfig` の環境変数上書きを検証するサンプル。 |
| `tests/test_worker_main.py` | stdin ループの JSON 取り回しを単体テストするパターン。 |
| `python/quality_config.py` | 品質閾値 (`<= 25%` や `<= 20 文字`) を環境変数で可変化するクラス。 |
| `notes/perf_logging.md` | `[PERF] capture=.. preproc=.. infer=.. postproc=.. total=..` 等のログ書式メモ。 |

> **Tips**
> - モバイル/U 系 CPU で大型 OCR モデルを常用するのは現実的ではありません。  
>   Windows.Media.Ocr など軽量 API を基本に据えて、ここで salvaged したテストやヒューリスティックだけ移植することを推奨します。
