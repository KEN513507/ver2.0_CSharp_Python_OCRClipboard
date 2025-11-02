# OCR Quality Improvement Tasks
#　TODOタスク
## Recently Completed
- [x] Automated test set creation with `tools/build_set1.ps1` (HTML → TXT/PNG/manifest)
- [x] Simplified README / documentation entry points (`docs/DOCUMENTATION_NAV.md`, `docs/OCR_TEST_SET1_PLAN.md`)

## 1. Enhance OCR Accuracy (src/python/ocr_worker/handler.py)
- [ ] Improve image preprocessing: add denoising, contrast enhancement, bilateral filtering
- [x] Switch from yomitoku to PaddleOCR for better accuracy (already imported in main.py)
- [ ] Add OCR parameter tuning (language detection, model selection)
- [ ] Auto-switch mono-code samples to EN model and adjust normalization/box-drawing stripping
- [ ] Implement fallback OCR engines if primary fails

## 2. Strengthen Quality Judgment Logic (src/python/ocr_worker/handler.py)
- [ ] Reduce error threshold from 10 to 5 characters
- [ ] Increase confidence threshold from 0.7 to 0.8
- [ ] Add text length validation (minimum length requirements)
- [ ] Add character pattern validation (detect obvious OCR failures)

## 3. Enhance Error Logging and Analysis (src/python/ocr_worker/handler.py, tests/scripts/analyze_ocr_errors.py)
- [ ] Add detailed error logging with context (image properties, preprocessing steps)
- [ ] Log common misrecognition patterns (character substitutions)
- [ ] Improve analyze_ocr_errors.py to visualize error patterns better
- [ ] Add false negative detection and logging

## 4. Fix and Enhance Testing (tests/scripts/test_ocr_accuracy.py)
- [x] Fix OCR result extraction from yomitoku/PaddleOCR
- [ ] Add comprehensive test patterns for different text types
- [ ] Focus on primary display scales (100%, 125%, 150%)
- [ ] Add real image testing alongside synthetic tests

## 5. Update Documentation / Ops Notes
- [x] Provide quick-start README + documentation map
- [ ] Clarify primary display only support with diagrams / screenshots
- [ ] Move quality thresholds・期待値 into a dedicated spec section
- [ ] Add troubleshooting section for OCR issues（ログ参照の仕方など）

## Followup Steps
- [ ] Run OCR accuracy tests after improvements
- [ ] Analyze error patterns and iterate
- [ ] Update quality report documentation
