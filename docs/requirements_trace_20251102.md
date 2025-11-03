# OCR Clipboard v2.0 要件トレーサビリティ（2025-11-02）

このドキュメントは、`PROJECT_SPEC.md` に記載されたプロダクト要件および追加仕様（`docs/ocr_overfit_analysis_20251102.md`）がどこまで実装済みかを整理するものです。各要件について現状・課題・対応すべき TODO をまとめています。

## 読む順序と関連資料
1. `docs/requirements_trace_20251102.md`（本書）… 最新の要件・仕様差分・実装状況を集約。
2. `PROJECT_SPEC.md` … UX フローやプロセス分解（P1〜P9）、時間配分などの背景設計。
3. `docs/DOCUMENTATION_NAV.md` … その他ドキュメント・ツール類の入口。

## 目次
- [1. プロダクト要件（PROJECT_SPEC.md）](#1-プロダクト要件project_specmd)
- [2. 追加技術要件（docsocr_overfit_analysis_20251102md）](#2-追加技術要件docsocr_overfit_analysis_20251102md)
- [3. テスト状況（TEST_FAILURES.md との整合）](#3-テスト状況test_failuresmd-との整合)
- [4. まとめ](#4-まとめ)
- [DFD / ER 図](#dfd--er-図)
## 1. プロダクト要件（PROJECT_SPEC.md）

| 要件 | 現状 | TODO / 課題 |
| --- | --- | --- |
| **10 秒以内の処理**<br>（ホットキー → OCR 結果出力が 10 秒未満） | `Program.cs` / `OCRClipboard.Overlay` でホットキー～キャプチャは実装済み。Python ワーカーは初回リクエスト時に PaddleOCR のモデルファイル読み込みと推論グラフ初期化を行うため、キャッシュ無し状態だと 10 秒超のウォームアップが発生（2 回目以降はキャッシュにより短縮）。 | `TODO_LIST.md` の「OCRWorker 品質判定の拡張」に SLA 計測の自動化を追加済み。処理時間ログの整備が未完。 |
| **誤差 ≤ 4 文字（品質制約）** | `tests/scripts/test_ocr_accuracy.py` で CER を評価し、閾値 0.30 を使用。Box-Drawing 除外により 002/008 の誤差が大きく改善。 | 本番ワーカー `handler.py` の `judge_quality` は厳しめ固定値のまま。`TODO.md` 2章「品質判定ロジック」の各項目が未対応。 |
| **WinUI3 + Python の二層構成** | `OCRClipboard.App`（WinUI3）と `src/python/ocr_worker`（PaddleOCR）が稼働。IPC は標準出力ベース。 | `TODO_LIST.md` にIPC強化や NamedPipe/gRPC 化のタスクは未記載。必要なら今後追加。 |
| **ホットキー → 矩形選択 → Capture → OCR パイプライン** | `PROJECT_SPEC.md` の P1～P9 に沿って概ね動作。キャプチャは `Windows.Graphics.Capture` を使用。現状はアプリ起動＝矩形選択開始で、グローバルホットキー (`RegisterHotKey` など) は未実装。 | DPI 125% 以上や複数モニター対応は `TODO_LIST.md` に「DPI スケール取得」「OverlayWindow の矩形補正」として進行中。グローバルホットキー実装は新規 TODO で追跡予定。 |
| **テスト画像セット（A1〜E1 / set1）** | `tools/build_set1.ps1` で再生成可能。`tests/scripts/test_ocr_accuracy.py` によりセット全体の CER を定期評価。 | 新たなパターン（多段レイアウト・実写など）は未整備。`TODO_LIST.md` に追加済み。 |

## 2. 追加技術要件（docs/ocr_overfit_analysis_20251102.md）

| 要件 | 現状 | TODO / 課題 |
| --- | --- | --- |
| **PaddleOCR 初期化時に環境変数を反映 (`use_dilation=True`)** | `tests/scripts/test_ocr_accuracy.py` の `_get_paddle()` で反映済み。Python ワーカー側でも `handler.py` が同様の環境変数を読むようになった。 | 値の調整やテストは継続余地。 |
| **Box-Drawing 文字 (U+2500–U+257F) を CER / 品質判定から除外** | テストスクリプトの `normalize_text()` で除去済み。要件クリア。 | 本番判定 (`judge_quality`) で同じフィルタを適用するタスクを `TODO_LIST.md` に追加済み。 |
| **`predict()` フォールバック削除** | `tests/scripts/test_ocr_accuracy.py` から削除。`TODO.md` の「Fix OCR result extraction …」を完了に更新済み。 | Python ワーカー側ではもともと `predict()` を使用していない。 |
| **`mono-code` タグの EN モデル切替 + 空白保持** | テストスクリプトでは未実装 (`lang_hint=EN` のみ `en` 使用)。 | `TODO.md` / `TODO_LIST.md` に「mono-code 判定の自動化 & Box-Drawing 除外」を追加済み。今後実装が必要。 |

## 3. テスト状況（TEST_FAILURES.md との整合）

| テスト名 | 現状 | 対応状況 |
| --- | --- | --- |
| `test_judge_quality_fail` | `judge_quality()` の閾値が厳しく、誤判定。Box-Drawing 除外では解決せず。 | `TODO.md` 2章の品質ロジック改善タスクが未着手。 |
| `test_calc_error_rate`, `test_clean_text` | 文字列処理ユーティリティの未修正でエラー発生。 | 別途修正が必要。 |
| Capture 系テスト (`test_capture_area_calculation` など) | `mss`, `pyperclip` 未導入でエラー。 | 依存関係インストールまたは条件付きスキップ要対応。 |

## 4. まとめ

- **満たしている要件**：PaddleOCR 初期化の環境変数適用、Box-Drawing 除外、`predict()` 廃止、検証環境での CER 評価仕組み。  
- **未達または進行中**：mono-code 自動判定、SLA (10 秒) の自動監視と改善、品質判定ロジックの微調整、DPI 対応の強化。  
- `TODO.md` / `TODO_LIST.md` に未達要件のタスクを追記済み。今後はこれらを消化しながらテスト (`tests/scripts/test_ocr_accuracy.py`) を定期的に実行し、`PROJECT_SPEC.md` のプロダクト要件を継続的に満たすことが目標。  
- `test_images/set1/012__JP__lowcontrast-dense.png` は既知の評価対象外（SLA 判定にも使用しない）とし、今後も参考データとして扱う。

### DFD / ER 図
- `PROJECT_SPEC.md` で示したレベル 0/1 の DFD を、本書でも最新状態として追跡します。
- ER 図（テキスト化されたデータストア・関係）は今後このドキュメントに追記予定です。

品質門番の優先順位：本番では `rule=levenshtein<=4` を最優先、評価時は `rule=cer<=thr` を採用。
既定挙動：タグ未指定のケースは JP モデル、`keep_spaces=False`、`ignore_boxdrawing=True` を適用。

更新日: 2025-11-02
