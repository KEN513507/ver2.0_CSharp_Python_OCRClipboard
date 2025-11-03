# OCR Clipboard v2.0 (Quick View)

**現状の制限（2025-11-03更新）**
- Display 1 専用・DPI 100% 前提で品質保証
- 日本語 UI の OCR 最適化中（誤差は原文の25%または20文字まで、10秒以内を目標）
- マハラノビス距離によるOCR品質異常検知機能追加（D² > 26.0で警告）
- 実機OCRは `pytest -m "slow"` で個別実行（通常テストから除外）
- CLI出力は stdout の JSON、stderr は人間向けログ

## クイックスタート

```bash
# Python環境セットアップ（ocr_worker用）
pip install -r src/python/requirements.txt

# C#アプリ実行
dotnet run --project src/csharp/OCRClipboard.App
```

## 本番直前チェックリスト（2025-11-03更新）

- `pip list --outdated` で非互換アップデートに注意
- `pip freeze > requirements.txt` で依存ファイルを最新化
- `pipdeptree` で依存関係のねじれ・重複を確認
- `pytest` で最低限のユニット・統合テストを実行
- `python tools/visualize_ocr_results.py` でマハラノビス異常検知テスト
- `gh workflow run` でGitHub ActionsのCIが正常稼働するか確認
- `git log --oneline --graph` でマージ/リベース履歴の破綻がないか確認
- 本番環境で `docker-compose run` など仮想テストを行い、環境差異・DLL・DPI問題を排除

---

最小限の情報だけをまとめた README です。詳しい流れは `docs/DOCUMENTATION_NAV.md` から辿れます。

## できること
````markdown
# OCR Clipboard v2.0 (Quick View)

最小限の情報だけをまとめた README です。詳しい流れは `docs/DOCUMENTATION_NAV.md` から辿れます。

**現状の制限（2025-10-30）**
- Display 1 専用・DPI 100% 前提で品質保証
- 日本語 UI の OCR 最適化中（誤差は原文の25%または20文字まで、10秒以内を目標）
- 実機OCRは `pytest -m "slow"` で個別実行（通常テストから除外）
- CLI出力は stdout の JSON、stderr は人間向けログ

## できること
- 最新の要件・DFD/ER 図は `docs/requirements_trace_20251102.md` に集約されています。本リポジトリで最優先に参照すべきドキュメントです。
- C# アプリが画面の選択範囲を取得 → Python OCR ワーカーへ JSON で依頼 → 認識結果をクリップボードへ
- 品質判定は Confidence + 編集距離。結果はログに残ります。

## まずはこれだけ
```powershell
pip install -r ocr_app/requirements.txt   # 初回の依存インストール
dotnet run --project src/csharp/OCRClipboard.App
```
- 指示どおりに範囲を選択すれば、`logs/debug_capture.png` とクリップボードに結果が出力されます。

## ドキュメント参照順
1. `docs/requirements_trace_20251102.md` … 最新要件・DFD/ER・テスト観点を集約した必読ドキュメント。
2. `PROJECT_SPEC.md` … ユーザー体験とプロセス分解（P1〜P9）、時間配分などの設計背景。
3. `docs/DOCUMENTATION_NAV.md` … 各資料への案内図と関連コマンド。

## フォルダのざっくり構成
- `src/csharp/OCRClipboard.App` … C# ホスト（Python に処理を渡す）
- `src/python/ocr_worker` … OCR 実体（json-over-stdio）
- `src/csharp/OCRClipboard.Overlay` … 範囲選択 UI
- `tests/` … 自動テスト
- `ocr_app/`, `ocr_sharp/`, `ocr_clipboard_app/` … PaddleOCR 関連ツールや設計メモ

## 注意点
- Display 1 / DPI 100% 前提
- 初回起動時は PaddleOCR モデルの読み込みと初期化が走るため、OCR 完了まで 10 秒前後かかる場合があります（2 回目以降はキャッシュ済みで短縮）。
- `PYTHONPATH=src/python` を設定して Python を起動
- 高速化（GPU / NamedPipe 等）は検証段階
- グローバルホットキーは未実装。アプリ起動と同時に選択 UI が開く現行仕様から、今後 `RegisterHotKey` を使った常駐トリガーへ拡張予定。
- Git 便利コマンド: `scripts/push_changes.ps1` を使用すると直近1時間の変更ファイル一覧を確認→Y/Nでコミット&pushまで自動化できます。PowerShell から `pwsh -File .\scripts\push_changes.ps1 -Message "メッセージ"` を実行してください（デフォルトで tracked のみステージング。`-IncludeUntracked` で新規ファイルも含められます）。
- 旧ワーカー `src/python/ocr_worker/main.py` は使用禁止。CI の `precheck_no_main_py` と pre-commit 用フックで検出されます。
  - ローカルでもチェックしたい場合は `git config core.hooksPath githooks` を一度実行してください。

---  
詳細を読みたくなったら `docs/DOCUMENTATION_NAV.md` を開いてください。
````
.\start_ocr_worker.cmd
