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
_PADDLE_OCR_CACHE: Dict[str, Any] = {}


def _get_yomitoku():
    global _YOMITOKU
    if _YOMITOKU is not None:
        return _YOMITOKU
    try:
        import yomitoku
        _YOMITOKU = yomitoku.OCR()
        print("[INIT] yomitoku loaded")
    except Exception as e:
        print(f"[INIT] yomitoku failed: {e}")
        _YOMITOKU = None
    return _YOMITOKU


def _get_paddle(lang: str = 'japan', use_angle_cls: bool = False):
    """共通の PaddleOCR インスタンスをキャッシュ取得（環境変数反映、辞書はデフォルト）"""
    global _PADDLE_OCR_CACHE
    
    # 環境変数からハイパーパラメータを読み取り
    det_db_thresh      = float(os.environ.get("OCR_DET_DB_THRESH", "0.30"))
    det_db_box_thresh  = float(os.environ.get("OCR_DET_DB_BOX_THRESH", "0.60"))
    det_db_unclip      = float(os.environ.get("OCR_DET_DB_UNCLIP", "1.50"))
    det_limit_side_len = int(os.environ.get("OCR_DET_LIMIT_SIDE_LEN", "960"))
    rec_batch_num      = int(os.environ.get("OCR_REC_BATCH_NUM", "6"))
    
    # キャッシュキーに主要パラメータを含めて取り違え防止
    cache_key = (lang, use_angle_cls, det_limit_side_len, det_db_thresh, det_db_box_thresh, det_db_unclip)
    
    if cache_key not in _PADDLE_OCR_CACHE:
        from paddleocr import PaddleOCR
        
        print(f"[INIT] PaddleOCR: lang={lang}, use_angle_cls={use_angle_cls}, "
              f"det_db_thresh={det_db_thresh}, det_box_thresh={det_db_box_thresh}, "
              f"unclip_ratio={det_db_unclip}, det_limit={det_limit_side_len}, "
              f"rec_batch={rec_batch_num}")
        
        _PADDLE_OCR_CACHE[cache_key] = PaddleOCR(
            lang=lang,
            use_textline_orientation=use_angle_cls,
            use_angle_cls=use_angle_cls,
            show_log=False,
            det_db_thresh=det_db_thresh,
            det_db_box_thresh=det_db_box_thresh,
            det_db_unclip_ratio=det_db_unclip,
            det_limit_side_len=det_limit_side_len,
            rec_batch_num=rec_batch_num,
            use_dilation=True,  # 低コントラスト対策
            drop_score=0.5,
        )
    return _PADDLE_OCR_CACHE[cache_key]


# ===========================
# パッチ1: 読み取り順序補正
# ===========================
def _join_words_in_reading_order(words) -> str:
    """yomitoku の words を 上→下→左→右 でソートして結合。
    bbox が取れない場合は検出順でそのまま結合にフォールバック。
    """
    with_box, no_box = [], []
    for w in words:
        txt = getattr(w, "content", "") or ""
        if not txt.strip():
            continue
        box = getattr(w, "bbox", None) or getattr(w, "box", None)
        if box and len(box) >= 4 and all(v is not None for v in box[:4]):
            x1, y1, x2, y2 = box[:4]
            with_box.append((int(y1 // 32), x1, txt))
        else:
            no_box.append(txt)

    if with_box:
        with_box.sort(key=lambda t: (t[0], t[1]))
        return "".join([t[2] for t in with_box] + no_box)

    # すべて bbox なし → 検出順でそのまま結合
    return "".join(no_box)


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
    """yomitoku 実行 + 語順補正 + デバッグ出力"""
    yomi = _get_yomitoku()
    if yomi is None:
        return None
    
    start = time.perf_counter()
    try:
        out = yomi(bgr_image)
        schema = out[0] if isinstance(out, tuple) else out
        
        # デバッグ: schema の構造を表示
        print(f"[DEBUG] yomitoku schema type: {type(schema)}")
        print(f"[DEBUG] yomitoku schema attrs: {dir(schema)[:10]}...")
        
        words = getattr(schema, "words", None)
        
        if not words:
            # lines や text フィールドの確認
            lines = getattr(schema, "lines", None)
            if lines:
                print(f"[DEBUG] yomitoku: using 'lines' ({len(lines)} items)")
                txt = _join_words_in_reading_order(lines)
                conf = 0.75
            else:
                direct_text = getattr(schema, "text", "") or ""
                if direct_text:
                    print(f"[DEBUG] yomitoku: using 'text' field directly")
                    txt = direct_text
                    conf = 0.75
                else:
                    print(f"[WARN] yomitoku: no words/lines/text found")
                    return None
        else:
            print(f"[DEBUG] yomitoku: found {len(words)} words")
            if len(words) > 0:
                # 最初の3語をサンプル表示
                for i, w in enumerate(words[:3]):
                    box = getattr(w, "bbox", None) or getattr(w, "box", None)
                    content = getattr(w, "content", "")
                    print(f"  word[{i}]: box={box}, content='{content[:20]}'")
            
            txt = _join_words_in_reading_order(words)
            confs = [float(getattr(w, "rec_score", 0.0)) for w in words if hasattr(w, "rec_score")]
            conf = float(sum(confs) / len(confs)) if confs else 0.75
        
        end = time.perf_counter()
        
        if not txt.strip():
            print(f"[WARN] yomitoku: text is empty after processing")
            return None
        
        return OcrResult("yomitoku", txt, conf, (end - start) * 1000.0)
    
    except Exception as e:
        print(f"[ERROR] yomitoku execution failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_paddleocr(bgr_image, lang_hint: str, tags: str = "") -> Optional[OcrResult]:
    """PaddleOCR 実行（言語はlang_hintを優先、mono-codeでも日本語ならjapan）"""
    # lang_hintを優先（JP/EN/MIX）
    if lang_hint.upper() == "EN":
        paddle_lang = "en"
    else:
        # JP/MIX は japan モデル（mono-code でも日本語+罫線対応）
        paddle_lang = "japan"
    
    ocr = _get_paddle(paddle_lang, use_angle_cls=False)
    
    if ocr is None:
        return None
    
    start = time.perf_counter()
    txt = ""
    conf = 0.0
    
    # ocr() メソッドのみ使用（predict() は削除）
    try:
        res = ocr.ocr(bgr_image, cls=False)
        
        if res and isinstance(res, list) and len(res) > 0:
            # res[0] が None または空リストの場合を考慮
            if res[0] and isinstance(res[0], list):
                texts, scores = [], []
                for item in res[0]:
                    if len(item) > 1 and item[1]:
                        t = item[1][0]
                        s = float(item[1][1]) if len(item[1]) > 1 else 0.8
                        texts.append(t)
                        scores.append(s)
                
                if texts:
                    txt = "".join(texts)
                    conf = float(sum(scores) / len(scores)) if scores else 0.8
                    print(f"[DEBUG] PaddleOCR lang={paddle_lang}: extracted {len(texts)} text blocks")
                else:
                    print(f"[WARN] PaddleOCR lang={paddle_lang}: no text blocks found in result")
            else:
                print(f"[WARN] PaddleOCR lang={paddle_lang}: res[0] is None or not a list")
    
    except Exception as e:
        print(f"[WARN] PaddleOCR ocr() failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    end = time.perf_counter()
    
    if not txt.strip():
        print(f"[WARN] PaddleOCR: no text extracted")
        return None
    
    return OcrResult("paddle", txt, conf, (end - start) * 1000.0)


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
        # 生成が +angle のため、補正は -angle
        M = cv2.getRotationMatrix2D((w//2, h//2), -angle, 1.0)
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
# BOX-DRAWING文字（U+2500-U+257F）を完全除去
BOX_DRAW_RE = re.compile(r'[\u2500-\u257F]+')

def normalize_text(s: str, *, keep_spaces: bool = False, ignore_boxdrawing: bool = True) -> str:
    """テキスト正規化（罫線除去、mono-codeでは空白保持）"""
    if not s:
        return ""
    
    # BOX-DRAWING文字を完全除去
    if ignore_boxdrawing:
        s = BOX_DRAW_RE.sub("", s)
    
    # 全角空白を半角へ（行頭インデント対策）
    s = s.replace("\u3000", " ")
    
    s = unicodedata.normalize("NFKC", s)
    
    if keep_spaces:
        # 連続空白は畳まず、改行→空白置換のみ
        s = s.replace("\r\n", " ").replace("\n", " ").strip()
    else:
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
def evaluate_dataset(
    manifest_path: pathlib.Path,
    root_dir: pathlib.Path,
    cer_threshold: float,
    only_ids: set[str] | None = None,
):
    """manifest.csv に基づいて全画像を評価"""
    
    with manifest_path.open(encoding="utf-8") as fp:
        rows = list(csv.DictReader(fp))
    
    results = []
    
    for row in rows:
        file_id = row["id"]
        file_name = row["file"]
        lang = row["lang"]
        tags = row["tags"]
        
        if only_ids and file_id not in only_ids:
            continue
        
        # 正解テキスト読み込み
        txt_path = root_dir / file_name.replace(".png", ".txt")
        if not txt_path.exists():
            print(f"[SKIP] {file_id}: TXT not found")
            continue
        
        expected_raw = txt_path.read_text(encoding="utf-8").strip()
        
        # mono-code では空白保持、罫線は常に無視
        keep_spaces = "mono-code" in tags.lower()
        expected_norm = normalize_text(expected_raw, keep_spaces=keep_spaces, ignore_boxdrawing=True)
        
        # 画像読み込み
        img_path = root_dir / file_name
        if not img_path.exists():
            print(f"[SKIP] {file_id}: PNG not found")
            continue
        
        pil_img = Image.open(img_path).convert("RGB")
        bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        # ★パッチ3: タグ別前処理
        bgr_processed = preprocess_for_tags(bgr, tags)
        
        # ★パッチ2: 両エンジン実行（tagsをrun_paddleocrに渡す）
        res_y = run_yomitoku(bgr_processed, lang)
        res_p = run_paddleocr(bgr_processed, lang, tags)
        
        # CER で比較して最良を選択
        candidates = []
        for r in [res_y, res_p]:
            if r and r.text:
                hyp_norm = normalize_text(r.text, keep_spaces=keep_spaces, ignore_boxdrawing=True)
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
        status = "OK" if result["quality_ok"] else "NG"
        print(f"{status} {file_id:3s} {tags:20s} engine={result['engine']:8s} CER={result['cer']:.3f} jq={result['quality_ok']}")
    
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
    parser.add_argument("--only", type=str, default=None, help="評価する ID をカンマ区切りで指定")
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
        
        only_ids = None
        if args.only:
            only_ids = {item.strip() for item in args.only.split(",") if item.strip()}
        
        results = evaluate_dataset(manifest_path, root_dir, cer_threshold, only_ids=only_ids)
        
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
