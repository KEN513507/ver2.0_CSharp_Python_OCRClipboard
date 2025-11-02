# OCR Clipboard v2.0 (Quick View)

最小限の情報だけをまとめた README です。詳しい流れは `docs/DOCUMENTATION_NAV.md` から辿れます。

## できること
- C# アプリが画面の選択範囲を取得 → Python OCR ワーカーへ JSON で依頼 → 認識結果をクリップボードへ
- 品質判定は Confidence + 編集距離。結果はログに残ります。

## まずはこれだけ
```powershell
pip install -r ocr_app/requirements.txt   # 初回の依存インストール
dotnet run --project src/csharp/OCRClipboard.App
```
- 指示どおりに範囲を選択すれば、`logs/debug_capture.png` とクリップボードに結果が出力されます。

## ドキュメントの入口
- `docs/DOCUMENTATION_NAV.md` … どこに何があるかの地図
- `docs/OCR_TEST_SET1_PLAN.md` … テストデータ set1 をワンコマンド生成する手順
- `tools/` … 自動化スクリプト群。`build_set1.ps1` の中身やフォント調整はここ
- `test_images/set1/` … 生成された `.txt` / `.png` / `manifest.csv` の保管場所
- `FACTORY_IMPROVEMENTS.md` … 手作業 → 自動化への改善履歴

## フォルダのざっくり構成
- `src/csharp/OCRClipboard.App` … C# ホスト（Python に処理を渡す）
- `src/python/ocr_worker` … OCR 実体（json-over-stdio）
- `src/csharp/OCRClipboard.Overlay` … 範囲選択 UI
- `tests/` … 自動テスト
- `ocr_app/`, `ocr_sharp/`, `ocr_clipboard_app/` … PaddleOCR 関連ツールや設計メモ

## 注意点
- Display 1 / DPI 100% 前提
- `PYTHONPATH=src/python` を設定して Python を起動
- 高速化（GPU / NamedPipe 等）は検証段階
- 旧ワーカー `src/python/ocr_worker/main.py` は使用禁止。CI の `precheck_no_main_py` と pre-commit 用フックで検出されます。
  - ローカルでもチェックしたい場合は `git config core.hooksPath githooks` を一度実行してください。

---  
詳細を読みたくなったら `docs/DOCUMENTATION_NAV.md` を開いてください。***
