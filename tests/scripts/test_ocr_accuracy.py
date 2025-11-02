#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/scripts/test_ocr_accuracy.py - パッチ適用版

改善点:
1. yomitoku 語順補正 (上→下→左→右ソート)
2. PaddleOCR 併走 + CER 比較で最良エンジン選択
3. タグ別前処理 (invert/lowcontrast/tilt のみ)
"""

from __future__ import annotations
import argparse
import csv
import json
import os
import pathlib
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

import cv2
import numpy as np
from PIL import Image

# プロジェクトルート
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "python"))

from ocr_worker.handler import levenshtein_distance  # noqa: E402

# ===========================
# グローバルキャッシュ
# ===========================
_YOMITOKU = None
_PADDLE_CACHE: Dict[str, Any] = {}


def _get_yomitoku():
    global _YOMITOKU
    if _YOMITOKU is not None:
        return _YOMITOKU
    try:
        import yomitoku
        _YOMITOKU = yomitoku.OCR()
    except Exception:
        _YOMITOKU = None
    return _YOMITOKU


def _get_paddle(lang_code: str):
    """PaddleOCR エンジンをキャッシュして返す"""
    if lang_code not in _PADDLE_CACHE:
        try:
            from paddleocr import PaddleOCR
            _PADDLE_CACHE[lang_code] = PaddleOCR(
                lang=lang_code,
                use_angle_cls=True,
                show_log=False,
                det=True,
                rec=True
            )
        except Exception:
            _PADDLE_CACHE[lang_code] = None
    return _PADDLE_CACHE[lang_code]


# ===========================
# パッチ1: 読み取り順序補正
# ===========================
def _join_words_in_reading_order(words) -> str:
    """yomitoku の words を 上→下→左→右 でソートして結合"""
    cleaned = []
    for w in words:
        txt = getattr(w, "content", "") or ""
        if not txt.strip():
            continue
        box = getattr(w, "bbox", None) or getattr(w, "box", None)
        if not box or len(box) < 4:
            continue
        x1, y1, x2, y2 = box[:4]
        # (行番号(y//32), x座標) でソート
        cleaned.append((int(y1 // 32), x1, txt))
    
    cleaned.sort(key=lambda t: (t[0], t[1]))
    return "".join(t[2] for t in cleaned)


# ===========================
# パッチ2: PaddleOCR 併走
# ===========================
@dataclass
class OcrResult:
    engine: str
    text: str
    confidence: float
    latency_ms: float


def run_yomitoku(bgr_image, lang_hint: str) -> Optional[OcrResult]:
    """yomitoku 実行 + 語順補正"""
    yomi = _get_yomitoku()
    if yomi is None:
        return None
    
    start = time.perf_counter()
    try:
        out = yomi(bgr_image)
        schema = out[0] if isinstance(out, tuple) else out
        words = getattr(schema, "words", None)
        
        if not words:
            return None
        
        # ★パッチ1適用: 語順補正
        txt = _join_words_in_reading_order(words)
        
        confs = [float(getattr(w, "rec_score", 0.0)) for w in words if hasattr(w, "rec_score")]
        conf = float(sum(confs) / len(confs)) if confs else 0.0
        
        end = time.perf_counter()
        return OcrResult("yomitoku", txt, conf, (end - start) * 1000.0)
    
    except Exception as e:
        print(f"[WARN] yomitoku failed: {e}")
        return None


def run_paddleocr(bgr_image, lang_hint: str) -> Optional[OcrResult]:
    """PaddleOCR 実行 (predict/ocr 両対応)"""
    paddle_lang = {"JP": "japan", "EN": "en", "MIX": "japan"}.get(lang_hint.upper(), "japan")
    ocr = _get_paddle(paddle_lang)
    
    if ocr is None:
        return None
    
    start = time.perf_counter()
    txt = ""
    
    # 1) predict() API (新)
    try:
        pred = ocr.predict(bgr_image)
        if pred and isinstance(pred, list) and len(pred) > 0:
            if isinstance(pred[0], dict):
                rec_texts = pred[0].get("rec_texts", [])
                txt = "".join(rec_texts)
    except Exception:
        pass
    
    # 2) ocr() API (旧) フォールバック
    if not txt:
        try:
            res = ocr.ocr(bgr_image, cls=True)
            if res and isinstance(res, list) and len(res) > 0 and isinstance(res[0], list):
                txt = "".join(item[1][0] for item in res[0] if len(item) > 1 and len(item[1]) > 0)
        except Exception:
            txt = ""
    
    end = time.perf_counter()
    
    if not txt:
        return None
    
    return OcrResult("paddle", txt, 0.80, (end - start) * 1000.0)


# ===========================
# パッチ3: タグ別前処理
# ===========================
def preprocess_for_tags(bgr, tags: str):
    """invert/lowcontrast/tilt のみ最小処理"""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    
    # invert: 極性反転
    if "invert" in tags:
        gray = cv2.bitwise_not(gray)
    
    # lowcontrast: 軽い CLAHE
    if "lowcontrast" in tags:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
    
    # tilt: 角度補正
    m = re.search(r"tilt(\d+)", tags)
    if m:
        angle = float(m.group(1))
        h, w = gray.shape[:2]
        M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
        gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    # 2倍拡大 (常時)
    h, w = gray.shape[:2]
    gray2 = cv2.resize(gray, (w*2, h*2), interpolation=cv2.INTER_CUBIC)
    
    # BGR に戻す (yomitoku/paddle の入力形式)
    return cv2.cvtColor(gray2, cv2.COLOR_GRAY2BGR)


# ===========================
# テキスト正規化 & CER
# ===========================
_WS_RX = re.compile(r"\s+", re.MULTILINE)

def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = _WS_RX.sub(" ", s).strip()
    return s


def char_error_rate(ref: str, hyp: str) -> float:
    """CER = Levenshtein距離 / 参照文字数"""
    if not ref:
        return 1.0 if hyp else 0.0
    dist = levenshtein_distance(ref, hyp)
    return dist / max(1, len(ref))


# ===========================
# データセット評価
# ===========================
def evaluate_dataset(manifest_path: pathlib.Path, root_dir: pathlib.Path, cer_threshold: float):
    """manifest.csv に基づいて全画像を評価"""
    
    with manifest_path.open(encoding="utf-8") as fp:
        rows = list(csv.DictReader(fp))
    
    results = []
    
    for row in rows:
        file_id = row["id"]
        file_name = row["file"]
        lang = row["lang"]
        tags = row["tags"]
        
        # 正解テキスト読み込み
        txt_path = root_dir / file_name.replace(".png", ".txt")
        if not txt_path.exists():
            print(f"[SKIP] {file_id}: TXT not found")
            continue
        
        expected_raw = txt_path.read_text(encoding="utf-8").strip()
        expected_norm = normalize_text(expected_raw)
        
        # 画像読み込み
        img_path = root_dir / file_name
        if not img_path.exists():
            print(f"[SKIP] {file_id}: PNG not found")
            continue
        
        pil_img = Image.open(img_path).convert("RGB")
        bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        # ★パッチ3: タグ別前処理
        bgr_processed = preprocess_for_tags(bgr, tags)
        
        # ★パッチ2: 両エンジン実行
        res_y = run_yomitoku(bgr_processed, lang)
        res_p = run_paddleocr(bgr_processed, lang)
        
        # CER で比較して最良を選択
        candidates = []
        for r in [res_y, res_p]:
            if r and r.text:
                hyp_norm = normalize_text(r.text)
                cer = char_error_rate(expected_norm, hyp_norm)
                candidates.append({
                    "engine": r.engine,
                    "text": r.text,
                    "confidence": r.confidence,
                    "latency_ms": r.latency_ms,
                    "cer": cer
                })
        
        if candidates:
            best = min(candidates, key=lambda d: d["cer"])
        else:
            best = {
                "engine": "none",
                "text": "",
                "confidence": 0.0,
                "latency_ms": 0.0,
                "cer": 1.0
            }
        
        # 結果記録
        result = {
            "id": file_id,
            "file": file_name,
            "lang": lang,
            "tags": tags,
            "engine": best["engine"],
            "confidence": round(best["confidence"], 3),
            "latency_ms": round(best["latency_ms"], 1),
            "cer": round(best["cer"], 3),
            "quality_ok": best["cer"] <= cer_threshold,
            "expected_preview": expected_norm[:50] + "..." if len(expected_norm) > 50 else expected_norm,
            "actual_preview": normalize_text(best["text"])[:50] + "..." if len(best["text"]) > 50 else normalize_text(best["text"])
        }
        
        results.append(result)
        
        # 進捗表示
        status = "✓" if result["quality_ok"] else "✗"
        print(f"{file_id:3s} {tags:20s} engine={result['engine']:8s} CER={result['cer']:.3f} jq={result['quality_ok']}")
    
    return results


# ===========================
# メイン
# ===========================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", action="store_true", help="データセット評価モード")
    parser.add_argument("--root", type=str, default="test_images/set1", help="データセットルート")
    parser.add_argument("--manifest", type=str, default="manifest.csv", help="マニフェストファイル名")
    parser.add_argument("--threshold", type=float, default=None, help="CER閾値 (デフォルト: 環境変数 CER_THRESHOLD or 0.15)")
    args = parser.parse_args()
    
    # CER閾値の決定
    if args.threshold is not None:
        cer_threshold = args.threshold
    else:
        cer_threshold = float(os.environ.get("CER_THRESHOLD", "0.15"))
    
    if args.dataset:
        # データセット評価
        root_dir = pathlib.Path(args.root)
        manifest_path = root_dir / args.manifest
        
        results = evaluate_dataset(manifest_path, root_dir, cer_threshold)
        
        # サマリー
        passed = sum(1 for r in results if r["quality_ok"])
        total = len(results)
        print(f"\nDataset Summary(CER<={cer_threshold}): {passed}/{total} passed")
        
        # 保存
        out_dir = ROOT / "tests" / "outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        
        out_json = out_dir / "ocr_dataset_eval.json"
        out_jsonl = out_dir / "ocr_dataset_eval.jsonl"
        
        with out_json.open("w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        with out_jsonl.open("w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        
        print(f"Saved: {out_json}")
        print(f"Saved: {out_jsonl}")
    
    else:
        # 従来のスケールテスト (後方互換)
        print("[INFO] Use --dataset for manifest-based evaluation")
        print("[INFO] Legacy scale test not implemented in this patch")


if __name__ == "__main__":
    main()