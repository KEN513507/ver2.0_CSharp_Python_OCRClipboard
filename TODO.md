# OCR Quality Improvement Tasks

## 1. Enhance OCR Accuracy (src/python/ocr_worker/handler.py)
- [ ] Improve image preprocessing: add denoising, contrast enhancement, bilateral filtering
- [ ] Switch from yomitoku to PaddleOCR for better accuracy (already imported in main.py)
- [ ] Add OCR parameter tuning (language detection, model selection)
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
- [ ] Fix OCR result extraction from yomitoku/PaddleOCR
- [ ] Add comprehensive test patterns for different text types
- [ ] Focus on primary display scales (100%, 125%, 150%)
- [ ] Add real image testing alongside synthetic tests

## 5. Update Documentation (README.md)
- [ ] Clarify primary display only support
- [ ] Add specification notes about current limitations
- [ ] Document quality thresholds and expectations
- [ ] Add troubleshooting section for OCR issues

## Followup Steps
- [ ] Run OCR accuracy tests after improvements
- [ ] Analyze error patterns and iterate
- [ ] Update quality report documentation
