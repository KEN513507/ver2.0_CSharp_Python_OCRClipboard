# OCR Profile Overfitting Analysis (2025-11-02)

> 最新の全体要件および DFD/ER 図は `docs/requirements_trace_20251102.md` に集約されています。本ドキュメントは補足分析として参照してください。

## Scope
- Script under test: `tests/scripts/test_ocr_accuracy.py`
- Data set: `test_images/set1` (12 samples, JP / EN / MIX)
- Focus samples: `002__JP__clean-dense.png`, `008__JP__mono-code.png`, `012__MIX__lowcontrast-dense.png`
- Worker backend: `src/python/ocr_worker/handler.py`

## Findings
1. **PaddleOCR hyperparameters not applied**
   - Logs show defaults (`det_db_thresh=0.30`, `det_db_box_thresh=0.60`, `det_db_unclip_ratio=1.5`, `det_limit_side_len=960`) regardless of environment variables.
   - Result: dense/low-contrast pages produce too few `dt_boxes` (e.g., sample 002 reduced to 3 boxes, sample 012 still `dt_boxes=0`).

2. **Stale `predict()` fallback**
   - The local script still calls `ocr.predict(...)`, which is not present in PaddleOCR 2.7.0.3, producing warnings and no usable output.

3. **Recognition dictionary not extended**
   - `rec_char_dict_path` remains the built-in `japan_dict.txt` / `en_dict.txt`; box-drawing characters are missing, causing sample 008 (mono-code) to degrade from CER 0.497 → 0.995.

4. **Normalization mismatch for mono-code samples**
    - Current CER normalization collapses spaces, which is harmful for code-like text. Combined with the default JP model, this yields near-random output for 008.

## Recommended Fixes
| Area | Action |
|------|--------|
| PaddleOCR init | Wrap `_get_paddle()` so it reads `OCR_DET_DB_THRESH`, `OCR_DET_DB_BOX_THRESH`, `OCR_DET_DB_UNCLIP`, `OCR_DET_LIMIT_SIDE_LEN`, `OCR_REC_BATCH_NUM`, `OCR_REC_CHAR_DICT`, and writes these into the PaddleOCR constructor. Include `use_dilation=True` for low-contrast pages. Cache key should include the tuned values. |
| Dictionary | Keep default dictionaries; instead strip Box-Drawing glyphs (U+2500–U+257F) from both reference and hypothesis before computing CER. |
| Execution path | Remove the obsolete `predict()` fallback; rely on `ocr(tile, cls=<...>)` and collect results from each tile. |
| Model selection & normalization | For tags containing `mono-code`, force the EN recognition head, skip aggressive whitespace normalization, and strip box-drawing glyphs during evaluation/runtime quality checks. |

## Test Harness
Suggested environment before running `tests/scripts/test_ocr_accuracy.py` (PowerShell notation):
```powershell
$env:OCR_DET_DB_THRESH      = "0.25"
$env:OCR_DET_DB_BOX_THRESH  = "0.55"
$env:OCR_DET_DB_UNCLIP      = "2.0"
$env:OCR_DET_LIMIT_SIDE_LEN = "1536"
$env:OCR_REC_BATCH_NUM      = "1"
# Optional: $env:OCR_REC_CHAR_DICT = "C:\path\to\custom_dict.txt"

python tests/scripts/test_ocr_accuracy.py --dataset --root test_images/set1 `
  --manifest manifest.csv --threshold 0.30 --only 002,008,012
```
**Expected outcome** after applying fixes (with box-drawing ignored during evaluation/runtime quality checks):
- Sample 002 CER ≈ 0.06–0.12 (dense text recovered)
- Sample 008 CER ≈ 0.15–0.22 (mono-code legible)
- Sample 012 CER ≈ 0.25–0.35 (low-contrast detection restored)

## Next Steps
1. Implement the four patches above in `tests/scripts/test_ocr_accuracy.py`.
2. Mirror hyperparameter support inside `src/python/ocr_worker/handler.py` so runtime OCR matches the test harness.
3. Re-run full dataset evaluation; target ≥ 11/12 `quality_ok`.
4. Archive this report with the corresponding commit and link from PR documentation.

## 要件定義（日本語サマリ）
- PaddleOCR 初期化時に環境変数 (`OCR_DET_DB_THRESH`, `OCR_DET_DB_BOX_THRESH`, `OCR_DET_DB_UNCLIP`, `OCR_DET_LIMIT_SIDE_LEN`, `OCR_REC_BATCH_NUM` など) を必ず反映し、低コントラスト対策として `use_dilation=True` を有効にすること。
- 文字辞書は既定のまま維持しつつ、CER 計算／本番品質判定の両方で Box-Drawing 文字 (U+2500–U+257F) を参照・結果から除去して無視すること。
- 廃止された `predict()` フォールバックを完全に削除し、`ocr(tile, cls=...)` の出力のみで文字列を組み立てること。
- `mono-code` タグを含むサンプルでは EN モデルを使いつつ空白正規化を緩和し、Box-Drawing 文字を除去した上で CER を算出すること。

### 要件と現状・TODO の突き合わせ

| 要件 | 現状 (`tests/scripts/test_ocr_accuracy.py`) | TODO 状態 |
|---|---|---|
| 1. PaddleOCR init を環境変数で制御 | `_get_paddle` が `OCR_*` 環境変数を読み込み、キャッシュキーに反映。`use_dilation=True` も設定済み。 | TODO には明記なし。要件は満たしたが値のチューニングは継続余地あり。 |
| 2. Box-Drawing 文字の除外 | `normalize_text()` で `BOX_DRAW_RE` を適用し CER 前に罫線を除去済み。 | TODO 該当なし。要件クリア。 |
| 3. `predict()` フォールバック削除 | `run_paddleocr()` は `ocr()` のみを呼び出し、`predict()` 分岐は削除済み。 | `TODO.md` #4 「Fix OCR result extraction…」の一部 → ✅ 済み。 |
| 4. mono-code 対応 | 現状 `lang_hint=EN` の場合だけ EN モデル使用。`mono-code` タグで自動切替＆空白保持は未対応。 | 新規 TODO として `TODO.md`／`TODO_LIST.md` に追記済み。 |

### TODO / TEST_FAILURES との整合
- `TODO.md` の「Fix OCR result extraction …」は完了済みとして更新済み。
- `mono-code` 自動判定＆空白調整は `TODO_LIST.md` に新規タスクとして追記。
- `TEST_FAILURES.md` の `test_judge_quality_fail` などは別系統の課題であり、今回の要件変更では未解決。個別対応が必要。
