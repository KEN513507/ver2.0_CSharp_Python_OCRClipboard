import importlib


def test_quality_env_override(monkeypatch):
    """
    QualityConfig が環境変数を優先することを確認するサンプル。
    """
    monkeypatch.setenv("OCR_MIN_CONFIDENCE", "0.5")
    monkeypatch.setenv("OCR_MAX_ABS_EDIT", "5")
    monkeypatch.setenv("OCR_MAX_REL_EDIT", "0.1")

    config = importlib.import_module("ocr_worker.config")
    importlib.reload(config)

    cfg = config.QualityConfig()
    assert cfg.min_confidence == 0.5
    assert cfg.max_abs_edit == 5
    assert abs(cfg.max_rel_edit - 0.1) < 1e-9


def test_nfkc_and_ignore_case_toggle(monkeypatch):
    """
    NFKC 正規化と大文字小文字の扱いを ON/OFF する動作チェック。
    """
    monkeypatch.setenv("OCR_BASE_ERROR_FLOOR", "0")
    monkeypatch.setenv("OCR_MAX_ABS_EDIT", "0")
    monkeypatch.setenv("OCR_MAX_REL_EDIT", "0")
    monkeypatch.setenv("OCR_MIN_CONF_LENGTH", "0")
    monkeypatch.setenv("OCR_MIN_CONFIDENCE", "0")

    monkeypatch.setenv("OCR_NORMALIZE_NFKC", "1")
    monkeypatch.setenv("OCR_IGNORE_CASE", "1")
    from ocr_worker.handler import judge_quality

    assert judge_quality("ＡＢＣ", "abc", 0.0)
    assert judge_quality("Hello", "hello", 0.0)

    monkeypatch.setenv("OCR_NORMALIZE_NFKC", "0")
    monkeypatch.setenv("OCR_IGNORE_CASE", "0")
    assert not judge_quality("ＡＢＣ", "abc", 0.0)
    assert not judge_quality("Hello", "hello", 0.0)
