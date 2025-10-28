# OCR品質評価レポート（2025年10月29日）

---

## 1. テスト・実行状況

- **pytestによる単体テスト（tests/test_handler.py）**
  - `test_judge_quality_fail`・`test_judge_quality_pass`ともに合格（品質判定ロジック自体は正常動作）。

- **OCR精度テストスクリプト（tests/scripts/test_ocr_accuracy.py）**
  - 3つのDPIスケール（1.0, 1.25, 1.5）でテスト実施。
  - すべてのスケールで品質判定NG（Quality OK: False）。
  - 実際のOCR抽出結果が空文字列（actual=''）、信頼度0.0、誤差値が異常（21896など）。
  - CUDA未使用（CPU動作）、TextDetector/TextRecognizerは正常に呼び出されているが、抽出結果が得られていない。

---

## 2. エラー・警告内容

- `TypeError: object of type 'OCRSchema' has no len()`
  - handler.pyの`levenshtein_distance`関数に渡すべきテキストがOCRSchema型になっていた（型不一致）。
  - このエラーは修正済み（以降は空文字列が渡されている）。

- `WARNING: OCR quality failed: expected='The quick brown fox jumps over the lazy dog.', actual='', confidence=0.0, error=44`
  - OCR抽出結果が空文字列となり、品質判定はすべて不合格。
  - 誤差値（Levenshtein距離）が異常値（21896）となっている。

---

## 3. ログ・出力

- TextDetector/TextRecognizerの初期化・実行時間は正常に記録。
- CUDA未使用の警告（CPUで処理）。
- 結果は`outputs/ocr_accuracy_test.json`に保存。
- サマリー：0/3 scales passed quality check（全スケール不合格）。

---

## 4. 現状の課題

- OCRエンジンが画像からテキストを抽出できていない（空文字列）。
- 品質判定ロジック自体は正常だが、入力データ（OCR抽出結果）が不正。
- 型不一致（OCRSchema型→str型）問題は修正済み。
- DPIスケールごとのテストは自動化されているが、OCR精度が根本的に不足。

---

## 5. 次のアクション例

- OCRエンジン（yomitoku等）の画像入力・前処理・パス指定を再確認。
- サンプル画像・テキストの対応関係、ファイルパス・形式を検証。
- 空文字列となる原因（画像パス不正、画像内容不適切、前処理不足等）を特定。
- ログ出力・エラー内容をもとに、OCR抽出部分のデバッグを優先。

---

#### 要約
品質判定ロジックは正常だが、OCR抽出結果が空文字列となり、すべての品質テストが不合格。
画像入力・OCRエンジンの動作確認・データ流れの再検証が必要です。
