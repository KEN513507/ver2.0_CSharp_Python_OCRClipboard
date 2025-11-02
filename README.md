# OCR Clipboard v2.0

このリポジトリは **C# と Python を組み合わせた OCR（文字読み取り）アプリ** の練習帳です。パソコンの画面で囲んだ場所を画像として保存し、Python で文字を読み取り、結果をクリップボードにコピーします。

## Table of Contents
- [Overview](#overview)
- [Documentation Index](#documentation-index)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Operational Notes](#operational-notes)
- [Known Limitations](#known-limitations)

## Overview
- **C# アプリ**が画面の選択範囲を受け取り、**Python アプリ**に「文字を読んで」と命令します。命令は JSON（見やすいテキスト形式）で送ります。
- 受け取った文字列は「正しい文章」と照らし合わせ、「どれくらい自信があるか（信頼度）」と「間違えた文字数（最大 4 文字まで OK）」の二本立てでチェックします。
- チェック結果はすべてログファイルに記録し、後から振り返れるようにします。

## Documentation Index
| Document | Scope |
| --- | --- |
| `README.md` (this file) | プロジェクト全体の概要、セットアップ、構成、制約。 |
| `ocr_app/CLI_SAMPLE_GUIDE.md` | PaddleOCR を使った軽量 **検証用 CLI スクリプト** の使い方。DPI 調査や単体実験向け。 |
| `ocr_sharp/OPERATIONS_GUIDE.md` | DPI 対応済みの Python ベース **実運用クライアント** の使い方。Tkinter + MSS による範囲選択。 |
| `ocr_clipboard_app/BLUEPRINT.md` | 将来追加予定の Windows 向けカスタムアプリの **設計メモ／ロードマップ**。現状は雛形のみ。 |

## Quick Start
1. **必要なツールを入れる**  
   - Python 3.10 以上  
   - .NET SDK 8.0 以上  
   - どちらもインストール後に `python --version` と `dotnet --version` で確認してください。
2. **Python 依存ライブラリを入れる**（PaddleOCR は `ocr_app/requirements.txt` にまとまっています）  
   ```pwsh
   pip install -r ocr_app/requirements.txt
   ```
3. **C# アプリを動かす**  
   ```pwsh
   dotnet run --project src/csharp/OCRClipboard.App
   ```  
   - 画面に「矩形を選んでください」と表示されたら、マウスで読み取りたい部分を囲みます。  
   - 取り込んだ画像は `logs/debug_capture.png` に保存されます。うまく選択できたか後で確認できます。

## Project Structure
- `src/csharp/OCRClipboard.App` – メインの C# アプリ。Python に命令を送り、結果を受け取ります。
- `src/csharp/OCRClipboard.Overlay` – 画面に半透明の四角を出して範囲を切り取る WPF アプリ。
- `src/python/ocr_worker` – 文字を読む Python 側のプログラム。
- `tests/` – 主要機能を自動で確認するテスト。
- `ocr_app/`, `ocr_sharp/`, `ocr_clipboard_app/` – 補助ツールと計画メモ。上記 Index から詳細を確認してください。

## Operational Notes
- C# から Python を呼び出すときは、環境変数 `PYTHONPATH=src/python` をセットして `ocr_worker` フォルダを読み込めるようにしています。
- Python 側は `-u` オプションを付けて実行し、結果を溜め込まずにすぐ C# に返します。
- 画面キャプチャは Display 1（メインモニタ）限定です。DPI（表示倍率）が 100% であることを前提にしています。
- 認識結果は  
  1. **Confidence（自信度）**  
  2. **Levenshtein 距離（何文字違うか）**  
  の 2 つで判定します。どちらかでも基準を下回ると「品質 NG」としてログに記録します。

## Known Limitations
- サブモニタ（Display 2 以降）では座標ズレが起きます。改善は今後の課題です。
- Windows の表示倍率を 125% 以上にすると計算が狂うため、現状では 100% のみをサポートしています。
- GPU を使った高速化、NamedPipe や gRPC など別の通信方式はまだ試作段階です。
- 問題を解決できたら、この項目も更新して通知します。
