# TODO Snapshot (2025-11-02)

| 状態 | 項目 | メモ / 次アクション |
| --- | --- | --- |
| ✅ | Set1 テストデータ自動化 | `tools/build_set1.ps1`・関連ドキュメント整備済み |
| ✅ | README / ドキュメント導線整理 | 最小構成に刷新。詳細は `docs/DOCUMENTATION_NAV.md` |
| 🟡 | DPI スケール取得・検証 | Display 1 以外対応が未完。補正ロジックを分離して調査継続 |
| 🟡 | OverlayWindow の矩形補正 | GraphicsCaptureItem の transform / HMONITOR 選択をテスト中 |
| 🟡 | 構造化ログ設計 + capture_diagnostics.jsonl | フォーマット案を固め、出力コードに組み込む |
| 🟡 | run_all_coordinate_tests.ps1 改修 | シナリオ分岐・自動判定を追加。工場の regression に組み込む |
| ⬜ | グローバルホットキーの実装 | `RegisterHotKey` と WinUI3 側ハンドラで起動トリガーを追加。Python 側 IPC 起動との整合も確認 |
| ⬜ | mono-code 判定の自動化 & Box-Drawing 除外 | EN モデル自動切替と評価ルール反映を実装 |
| ⬜ | OCRWorker 品質判定の拡張 | 誤差ログ・タイムアウト処理を入れる。品質閾値の最終決定とセットで実装 |
| ⬜ | README / PROJECT_SPEC.md の仕様反映 | Display 制約・品質閾値をまとめ、外部共有できる形にする |
| ⬜ | テストパターン HTML のズレ可視化強化 | set1 以外の画像化テンプレートを検討（多段レイアウト等） |
| ⬜ | 全体リファクタリング | コード整理・古い TODO の棚卸し（このファイル含む） |

凡例: ✅ 完了 / 🟡 進行中 / ⬜ 未着手
