import os
import json
import pytest
import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import scan_clipboard

# --- 1. 純粋関数のテスト (Logic) ---

def test_wrap_with_prompt_full_mode():
    config = {"clipboard_wrapper": {"prefix_text": "PRE", "suffix_text": "SUF"}}
    assert scan_clipboard.wrap_with_prompt("CONTENT", config, raw_mode=False) == "PRE\n\nCONTENT\n\nSUF"

def test_wrap_with_prompt_raw_mode():
    config = {"clipboard_wrapper": {"prefix_text": "PRE", "suffix_text": "SUF"}}
    assert scan_clipboard.wrap_with_prompt("CONTENT", config, raw_mode=True) == "CONTENT"

def test_load_config_invalid_json(tmp_path):
    """異常系: 壊れたJSONのハンドリング"""
    bad_config = tmp_path / "bad.json"
    bad_config.write_text("{ invalid }")
    assert scan_clipboard.load_config(bad_config) == {}

@patch("builtins.open", side_effect=IOError("Permission denied"))
def test_load_config_io_error(mock_open):
    """異常系: ファイルが読めない時のハンドリング"""
    assert scan_clipboard.load_config(Path("some_file")) == {}

# --- 2. Side Effects のテスト (Mocks) ---

@patch("shutil.which")
def test_command_exists(mock_which):
    mock_which.return_value = "/usr/bin/ls"
    assert scan_clipboard.command_exists("ls") is True

@patch("scan_clipboard.ImageAnnotatorClient")
def test_get_ocr_text_flow(mock_client_class, tmp_path):
    mock_client = MagicMock()
    mock_anno = MagicMock()
    mock_anno.description = "TEXT"
    mock_client.text_detection.return_value.text_annotations = [mock_anno]
    img = tmp_path / "t.png"
    img.write_bytes(b"d")
    assert scan_clipboard.get_ocr_text(str(img), client_factory=lambda: mock_client) == "TEXT"

@patch("subprocess.run")
@patch("os.path.exists")
@patch("os.remove")
def test_capture_area_with_cleanup(mock_remove, mock_exists, mock_run):
    """既存の画像がある場合の削除ロジックをテスト"""
    mock_exists.return_value = True
    assert scan_clipboard.capture_area("out.png") == "out.png"
    mock_remove.assert_called_once_with("out.png")

@patch("subprocess.run")
def test_copy_to_clipboard_all_paths(mock_run):
    """成功と失敗の両方のパスを通す"""
    mock_run.return_value = MagicMock(returncode=0)
    assert scan_clipboard.copy_to_clipboard("ok") is True
    
    mock_run.side_effect = Exception("xclip failed")
    assert scan_clipboard.copy_to_clipboard("fail") is False

# --- 3. メインフローのテスト (Integration via Mocks) ---

@patch("scan_clipboard.check_required_commands")
@patch("scan_clipboard.capture_area", return_value="f.png")
@patch("scan_clipboard.get_ocr_text", return_value="HELLO")
@patch("scan_clipboard.load_config", return_value={})
@patch("scan_clipboard.copy_to_clipboard", return_value=True)
def test_main_full_flow(mock_copy, mock_load, mock_get, mock_cap, mock_check):
    with patch("sys.exit") as mock_exit:
        scan_clipboard.main()
        mock_exit.assert_not_called()

@patch("scan_clipboard.check_required_commands")
@patch("scan_clipboard.capture_area", return_value="f.png")
@patch("scan_clipboard.get_ocr_text", side_effect=Exception("Unexpected API Error"))
def test_main_error_handling(mock_get, mock_cap, mock_check):
    """予期せぬエラーが起きた時にクラッシュせず exit(1) することを確認"""
    with patch("sys.exit", side_effect=SystemExit(1)) as mock_exit:
        with pytest.raises(SystemExit) as e:
            scan_clipboard.main()
        assert e.value.code == 1

@patch("scan_clipboard.command_exists", return_value=False)
def test_check_required_commands_exit(mock_exists):
    with patch("sys.exit", side_effect=SystemExit(1)) as mock_exit:
        with pytest.raises(SystemExit) as e:
            scan_clipboard.check_required_commands()
        assert e.value.code == 1
