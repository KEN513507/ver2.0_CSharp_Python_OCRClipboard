# Documentation Quick Navigation

よく使うドキュメントと実行ポイントを 1 ページにまとめました。詳しい説明は各リンク先で確認してください。

| 行動したいこと | 見る場所 | ひとことメモ |
| --- | --- | --- |
| プロジェクト全体の概要 / セットアップを知りたい | `README.md` | C# × Python の仕組み、Quick Start、ディレクトリ構成 |
| OCR テストデータ (set1) を生成したい | `docs/OCR_TEST_SET1_PLAN.md` | `pwsh tools/build_set1.ps1 -Html ocr_test_set1_corpus_corrected.html` で全自動。スポットチェックの手順付き |
| テキスト抽出 / PNG 生成などのスクリプト処理を確認したい | `tools/` フォルダ | `extract_texts.py`, `build_manifest.py`, `generate_images.py`, `build_set1.ps1` が役割ごとに分担 |
| 生成された成果物を確認したい | `test_images/set1/` | `.txt` / `.png` / `manifest.csv` をセットで管理。Raw/Norm の回帰チェックには `scripts/run_polarity_batch.ps1` |
| テスト自動化や品質改善の経緯を知りたい | `FACTORY_IMPROVEMENTS.md` | 手作業 → 自動化までの改善ログ。今後の拡張案もこちら |
| PaddleOCR CLI 検証サンプルを動かしたい | `ocr_app/CLI_SAMPLE_GUIDE.md` | 単体検証用の Python スクリプト。DPI 調査などに使用 |
| DPI 対応済みクライアント（Python）を触りたい | `ocr_sharp/OPERATIONS_GUIDE.md` | Tkinter + MSS で実運用に近いクライアント |
| 将来の Windows カスタムアプリ構想を確認したい | `ocr_clipboard_app/BLUEPRINT.md` | まだ雛形。設計メモと TODO |

## すぐ実行したいコマンド

```powershell
# 1. 前提ライブラリ（初回のみ）
pip install beautifulsoup4 pillow

# 2. テストセット (set1) を生成
pwsh tools/build_set1.ps1 -Html ocr_test_set1_corpus_corrected.html

# 3. スポットチェック後、Git に保存
git add test_images/set1/*
git commit -m "Add OCR test set 1"
git push

# 4. OCR 精度テスト（任意）
python tests/scripts/test_ocr_accuracy.py test_images/set1/manifest.csv
```

## 補足
- HTML コーパスを更新したら上記コマンドを再実行して PNG/TXT/manifest を再生成してください。
- フォント変更やタグ追加は `tools/generate_images.py` を編集すると即座に反映されます。
- さらなる自動化や改善アイデアは `FACTORY_IMPROVEMENTS.md` に追記すると管理しやすくなります。
