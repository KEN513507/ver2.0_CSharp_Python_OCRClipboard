# テスト失敗・エラー一覧（2025-10-30）

## 失敗したテスト

- **test_judge_quality_fail (test_handler.py)**
  - 内容: judge_quality関数が誤った結果を返している
- **test_calc_error_rate (test_utils.py)**
  - 内容: calc_error_rate関数でIndexErrorが発生
- **test_clean_text (test_utils.py)**
  - 内容: clean_text関数が期待されたテキストを含んでいない

## エラーが発生したテスト

- **test_normalize_bbox_zero_size (test_bbox.py)**
  - 内容: ZeroDivisionError
- **test_capture_area_calculation (test_capture.py)**
  - 内容: ModuleNotFoundError (mssモジュールがない)
- **test_main_capture_integration (test_capture.py)**
  - 内容: ModuleNotFoundError (pyperclipモジュールがない)
- **test_select_capture_area (test_capture.py)**
  - 内容: ModuleNotFoundError (mssモジュールがない)
