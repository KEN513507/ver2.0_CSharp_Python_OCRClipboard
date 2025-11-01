# TODO（2025-11-01 更新）

## 完了済み ✅

- Windows.Media.Ocr エンジン実装／日本語言語優先
- Display 1 / DPI 100% のオーバーレイと座標ログ
- 薄い選択に対する警告・上下 8px パディング
- `[PERF]` / `[OCR]` / `[CLIPBOARD]` ログ整形
- `scripts/run_dev_checks.ps1` による CI と同等のローカルチェック
- xUnit テストプロジェクト (`tests/OCRClipboard.Tests`)

## 優先タスク 🎯

1. **トレイ常駐 & ホットキー**
   - [ ] `NotifyIcon` 常駐化（終了メニュー含む）
   - [ ] `RegisterHotKey` で Ctrl+Shift+O を割り当て
   - [ ] 安全な終了処理（F-1/F-2/F-5 達成）

2. **品質判定の配線**
   - [ ] `OcrQualityEvaluator` を `Program.cs` に組み込み CER/Accuracy を算出
   - [ ] `[QUALITY] cer=.. accuracy=..` をログ出力
   - [ ] 品質 NG 時の挙動（警告と非コピー）を決定

3. **非機能メトリクスの実測**
   - [ ] `dotnet publish` で self-contained バイナリサイズを計測（NF-3）
   - [ ] 実行時メモリ使用量を計測し README/PROJECT_SPEC に追記（NF-4）

4. **ドキュメントの継続整備**
   - [ ] Slow テスト運用方針（self-hosted runner 含む）を `docs/CI_CD_STRATEGY.md` に追記
   - [ ] `start_ocr_worker.cmd` がレガシーである旨をドキュメントに明記済みか確認

## 将来検討

- 品質ログの可視化（`QualityConfig` の実値を起動時ログに出す）
- Display 2 / DPI 125% テスト用の E2E スクリプト（必要なら）
- SlowOCR（実機）テストの実装と self-hosted runner 導入
- クリップボードへの重複書き込み抑止、最小長ヒューリスティックなど細かな UX 改善
