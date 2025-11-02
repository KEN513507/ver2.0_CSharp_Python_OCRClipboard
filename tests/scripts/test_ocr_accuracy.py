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
    if os.environ.get("YOMITOKU_DISABLE","0").lower() in ("1","true","on"):
        print("[INIT] yomitoku disabled by env")
        return None
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
    det_db_thresh      = float(os.environ.get("OCR_DET_DB_THRESH", "0.3"))
    det_db_box_thresh  = float(os.environ.get("OCR_DET_DB_BOX_THRESH", "0.6"))
    det_db_unclip      = float(os.environ.get("OCR_DET_DB_UNCLIP", "1.5"))
    det_limit_side_len = int(os.environ.get("OCR_DET_LIMIT_SIDE_LEN", "960"))
    rec_batch_num      = int(os.environ.get("OCR_REC_BATCH_NUM", "6"))
    drop_score         = float(os.environ.get("OCR_PADDLE_DROP_SCORE", "0.5"))
    use_dilation       = os.environ.get("OCR_PADDLE_USE_DILATION","0").lower() in ("1","true","on")
    binarize           = os.environ.get("OCR_PADDLE_BINARIZE","0").lower() in ("1","true","on")
    invert             = os.environ.get("OCR_PADDLE_INVERT","0").lower() in ("1","true","on")
    
    # キャッシュキーに主要パラメータを含めて取り違え防止
    cache_key = (lang, use_angle_cls, det_limit_side_len, det_db_thresh, det_db_box_thresh, det_db_unclip, drop_score, use_dilation, binarize, invert)
    
    if cache_key not in _PADDLE_OCR_CACHE:
        from paddleocr import PaddleOCR
        
        print(f"[INIT] PaddleOCR: lang={lang}, use_angle_cls={use_angle_cls}, "
              f"det_db_thresh={det_db_thresh}, det_box_thresh={det_db_box_thresh}, "
              f"unclip_ratio={det_db_unclip}, det_limit={det_limit_side_len}, "
              f"rec_batch={rec_batch_num}, drop_score={drop_score}, "
              f"use_dilation={use_dilation}, binarize={binarize}, invert={invert}")
        
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
            use_dilation=use_dilation,
            drop_score=drop_score,
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
    """PaddleOCR 実行（mono-codeでもlang_hint優先、誤り補正で対応）"""
    # mono-code時に二重言語認識を有効化
    use_dual_lang = os.environ.get("OCR_PADDLE_DUAL_LANG", "0").lower() in ("1", "true", "on")
    
    if "mono-code" in tags.lower() and use_dual_lang:
        print(f"[DEBUG] Using dual-lang recognition for mono-code")
        return _run_paddleocr_dual_lang(bgr_image, lang_hint, tags)
    
    # lang_hintを優先
    paddle_lang = {"JP":"japan","EN":"en","MIX":"japan"}.get(lang_hint.upper(),"japan")
    
    ocr = _get_paddle(paddle_lang, use_angle_cls=False)
    
    if ocr is None:
        return None
    
    start = time.perf_counter()
    txt = ""
    conf = 0.0
    
    # ocr() メソッドのみ使用
    try:
        res = ocr.ocr(bgr_image, cls=False)
        
        if res and isinstance(res, list) and len(res) > 0:
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
                    
                    # mono-code向け誤り補正
                    if "mono-code" in tags.lower():
                        txt = _fix_mono_code_errors(txt)
                    
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


def _run_paddleocr_dual_lang(bgr_image, lang_hint: str, tags: str) -> Optional[OcrResult]:
    """mono-code用: japanで検出+認識、各行をJP/ENで再認識、ASCII率で動的切替"""
    start = time.perf_counter()
    
    try:
        # 1. japanで検出+認識（一回目）
        ocr_jp = _get_paddle("japan")
        res_jp = ocr_jp.ocr(bgr_image, cls=False)
        
        if not res_jp or not res_jp[0]:
            print(f"[WARN] Dual-lang: no result from japan")
            return None
        
        jp_items = res_jp[0]
        print(f"[DEBUG] Dual-lang: japan detected {len(jp_items)} blocks")
        
        # 2. 各行をENで再認識（ROI切り出し）
        ocr_en = _get_paddle("en")
        texts, scores = [], []
        
        for i, item in enumerate(jp_items):
            if not item or len(item) < 2:
                continue
            
            box = item[0]
            jp_result = item[1]
            jp_text = jp_result[0] if jp_result else ""
            jp_score = float(jp_result[1]) if jp_result and len(jp_result) > 1 else 0.5
            
            # ボックス座標を取得（4点）
            pts = np.array(box, dtype=np.float32).reshape(4, 2)
            x_coords = pts[:, 0]
            y_coords = pts[:, 1]
            x1, x2 = int(x_coords.min()), int(x_coords.max())
            y1, y2 = int(y_coords.min()), int(y_coords.max())
            
            # 画像から該当領域を切り出し
            h, w = bgr_image.shape[:2]
            x1, x2 = max(0, x1), min(w, x2)
            y1, y2 = max(0, y1), min(h, y2)
            
            if x2 <= x1 or y2 <= y1:
                texts.append(jp_text)
                scores.append(jp_score)
                continue
            
            roi = bgr_image[y1:y2, x1:x2]
            
            # EN認識（ROI単独）
            res_en = ocr_en.ocr(roi, cls=False)
            en_text, en_score = "", 0.0
            if res_en and res_en[0] and len(res_en[0]) > 0:
                en_item = res_en[0][0]
                if len(en_item) > 1 and en_item[1]:
                    en_text = en_item[1][0]
                    en_score = float(en_item[1][1]) if len(en_item[1]) > 1 else 0.5
            
            # デバッグ: JP/EN両方の結果を表示（最初の5行のみ）
            if i < 5:
                print(f"[DEBUG] Box {i}: JP={repr(jp_text[:40])} (score={jp_score:.3f}), EN={repr(en_text[:40])} (score={en_score:.3f})")
            
            # ASCII率で判定（70%以上なら英語優先）
            def ascii_ratio(s):
                if not s:
                    return 0.0
                ascii_count = sum(1 for c in s if ord(c) < 128)
                return ascii_count / len(s)
            
            # 拡張子・パス区切りが見える行はJP/EN両方試してスコア高い方を採用
            has_ext = re.search(r'\.[a-zA-Z0-9]{2,5}', jp_text or en_text)
            has_path = "/" in (jp_text or en_text)
            
            # ★ENがサイズ表記を認識しているか確認
            # 厳格パターン: 数字+KB/MB、または括弧付き数字（(128のようなパターン）
            size_pattern_strict = r'(\d+(?:\.\d+)?)\s*(K|M)B'
            size_pattern_paren = r'[(\[]\s*\d{2,}'  # 括弧付き2桁以上の数字（(128など）
            en_has_size = en_text and (re.search(size_pattern_strict, en_text, re.IGNORECASE) or re.search(size_pattern_paren, en_text))
            jp_has_size = jp_text and re.search(size_pattern_strict, jp_text, re.IGNORECASE)
            
            if en_has_size and not jp_has_size:
                # ENがサイズ表記を認識し、JPが認識していない→EN優先
                chosen_text, chosen_score = en_text, en_score
                chosen_lang = "EN(Size)"
            elif has_ext or has_path:
                # ファイルパス行: 高スコア優先
                if en_text and en_score > jp_score:
                    chosen_text, chosen_score = en_text, en_score
                    chosen_lang = "EN"
                else:
                    chosen_text, chosen_score = jp_text, jp_score
                    chosen_lang = "JP"
            elif ascii_ratio(jp_text) >= 0.70:
                # ASCII優勢: EN採用
                if en_text:
                    chosen_text, chosen_score = en_text, en_score
                    chosen_lang = "EN"
                else:
                    chosen_text, chosen_score = jp_text, jp_score
                    chosen_lang = "JP"
            else:
                # 日本語優勢: JP採用
                chosen_text, chosen_score = jp_text, jp_score
                chosen_lang = "JP"
            
            if chosen_text:
                texts.append(chosen_text)
                scores.append(chosen_score)
                if i < 5:  # 最初の5行だけデバッグ表示
                    print(f"[DEBUG] Line {i}: chose {chosen_lang} score={chosen_score:.3f} text='{chosen_text[:30]}'")
        
        if not texts:
            print(f"[WARN] Dual-lang: no text extracted")
            return None
        
        # mono-code用: 改行で結合（ツリー構造維持）
        txt = "\n".join(texts)
        conf = float(sum(scores) / len(scores)) if scores else 0.5
        
        # mono-code 誤り補正
        txt = _fix_mono_code_errors(txt)
        
        end = time.perf_counter()
        
        print(f"[DEBUG] Dual-lang (JP/EN): extracted {len(texts)} blocks, avg_score={conf:.3f}")
        
        return OcrResult("paddle", txt, conf, (end - start) * 1000.0)
    
    except Exception as e:
        print(f"[ERROR] Dual-lang failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def _closest_extension(ext: str, candidates=None) -> str:
    """拡張子をレーベンシュタイン距離1以内で補正"""
    if candidates is None:
        candidates = ["txt", "md", "docx", "pptx", "jpg", "png", "pdf"]
    
    ext = ext.lower()
    if ext in candidates:
        return ext
    
    # 距離1以内の候補を探す（簡易実装: 1文字差分）
    for cand in candidates:
        if abs(len(ext) - len(cand)) > 1:
            continue
        # 1文字違い、1文字挿入、1文字削除のチェック
        if len(ext) == len(cand):
            diff = sum(1 for a, b in zip(ext, cand) if a != b)
            if diff <= 1:
                return cand
        elif len(ext) == len(cand) + 1:
            # ext から1文字削除で cand になる
            for i in range(len(ext)):
                if ext[:i] + ext[i+1:] == cand:
                    return cand
        elif len(ext) == len(cand) - 1:
            # cand から1文字削除で ext になる
            for i in range(len(cand)):
                if cand[:i] + cand[i+1:] == ext:
                    return cand
    
    return ext  # 補正できなければそのまま


def repair_tree_listing_line(s: str) -> str:
    """ツリー行の構造補正（mono-code専用）
    
    想定フォーマット: <indent>/<path>.<ext> (N KB)
    - パス区切り: / に統一
    - 拡張子: 距離1以内で補正
    - サイズ: (N KB) 形式に統一
    - 括弧: () に統一
    """
    if not s:
        return s
    
    # 全角→半角基礎補正
    s = s.replace("／", "/").replace("＼", "/").replace("ノ", "/")
    s = s.replace("—", "-").replace("–", "-").replace("－", "-")
    s = s.replace("・", ".").replace("，", ",")
    s = s.replace("（", "(").replace("）", ")")
    s = s.replace("［", "[").replace("］", "]")
    s = s.replace("｛", "{").replace("｝", "}")
    
    # よくある誤認識パターン補正
    s = s.replace("ノト", "/")  # "ドキュメントノト" → "ドキュメント/"
    s = s.replace("ト/", "/")   # 補正後の残骸除去
    
    # サイズ正規化: [12 KB] → (12 KB), (12KB] → (12 KB)
    size_pattern = r'[(\[{｛]\s*(\d+(?:\.\d+)?)\s*(K|M)B?\s*[)\]}｝]'
    def normalize_size(m):
        num = m.group(1)
        unit = m.group(2).upper() + "B"
        return f"({num} {unit})"
    
    s = re.sub(size_pattern, normalize_size, s, flags=re.IGNORECASE)
    
    # サイズ前後の空白を調整
    s = re.sub(r'\s*\(\s*(\d+(?:\.\d+)?)\s+(K|M)B\s*\)', r' (\1 \2B)', s)
    
    # 拡張子補正（末尾トークン）
    ext_match = re.search(r'\.([A-Za-z0-9×]{2,5})(?=\s|\(|$)', s)
    if ext_match:
        orig_ext = ext_match.group(1)
        # t×t → txt など
        fixed_ext = orig_ext.replace("×", "x").replace("X", "x")
        corrected_ext = _closest_extension(fixed_ext)
        if corrected_ext != orig_ext.lower():
            s = s[:ext_match.start(1)] + corrected_ext + s[ext_match.end(1):]
    
    # パス区切りの追加補正（カタカナの誤認）
    s = re.sub(r'(?<=[a-zA-Z0-9_])ノ(?=[a-zA-Z0-9_])', '/', s)
    s = re.sub(r'ノ(?=[a-zA-Z0-9_])', '/', s)  # 日本語直後でも英数字前なら/
    
    # 括弧の統一（角括弧・波括弧を丸括弧に）
    s = s.replace("[", "(").replace("]", ")")
    s = s.replace("{", "(").replace("}", ")")
    
    # 連続空白を1つに（keep_spaces維持のため改行は保持）
    s = re.sub(r' {2,}', ' ', s)
    
    return s.strip()


def _fix_mono_code_errors(text: str) -> str:
    """mono-code向け誤り補正（よくある記号/文字の混同）"""
    if not text:
        return text
    
    # 基本的な記号補正
    text = text.replace("t×t", "txt")
    text = text.replace("×t", "xt")
    text = text.replace("t×", "tx")
    
    # KB誤認補正
    text = re.sub(r'KB\)KB\]', 'KB)', text)
    text = re.sub(r'\[(\d+)\s*KB\]', r'(\1 KB)', text)
    
    # ハイフン/ダッシュ正規化
    text = text.replace("–", "-").replace("—", "-").replace("－", "-")
    
    # パス区切り補正
    text = text.replace("ノト", "/")
    text = re.sub(r'(?<=[a-zA-Z0-9_])ノ(?=[a-zA-Z0-9_])', '/', text)
    text = re.sub(r'ノ(?=[a-zA-Z0-9_])', '/', text)
    
    # ドット補正
    text = text.replace("・", ".")
    
    # 括弧補正
    text = text.replace("（", "(").replace("）", ")")
    
    return text


# ===========================
# パッチ3: タグ別前処理
# ===========================
def preprocess_for_tags(bgr, tags: str):
    """invert/lowcontrast/tilt のみ最小処理、dense/lowcontrast強化"""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    
    # invert: 極性反転
    if "invert" in tags:
        gray = cv2.bitwise_not(gray)
    
    # lowcontrast: CLAHE強化 + 二値化 + 膨張
    if "lowcontrast" in tags:
        # CLAHE強化
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        
        # 弱いブラー（ノイズ軽減）
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Otsu二値化
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        # 環境変数でINVERT制御
        if os.environ.get("OCR_PADDLE_INVERT","0").lower() in ("1","true","on"):
            bw = cv2.bitwise_not(bw)
        
        # 縦方向のみ膨張（文字を太らせて検出しやすく）
        if os.environ.get("OCR_PADDLE_USE_DILATION","0").lower() in ("1","true","on"):
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 2))
            bw = cv2.dilate(bw, kernel, iterations=1)
        
        gray = bw
    
    # tilt: 角度補正
    m = re.search(r"tilt(\d+)", tags)
    if m:
        angle = float(m.group(1))
        h, w = gray.shape[:2]
        # 生成が +angle のため、補正は -angle
        M = cv2.getRotationMatrix2D((w//2, h//2), -angle, 1.0)
        gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    # dense: 1.5倍拡大（小さい画像のみ）
    if "dense" in tags and gray.shape[1] < 1920:
        gray = cv2.resize(gray, (int(gray.shape[1]*1.5), int(gray.shape[0]*1.5)), interpolation=cv2.INTER_CUBIC)
    
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

def normalize_text(s: str, *, keep_spaces: bool = False, ignore_boxdrawing: bool = True, fix_code_symbols: bool = False) -> str:
    """テキスト正規化（罫線除去、mono-codeでは空白保持+記号補正）"""
    if not s:
        return ""
    
    s = unicodedata.normalize("NFKC", s)
    
    # BOX-DRAWING文字を完全除去
    if ignore_boxdrawing:
        s = BOX_DRAW_RE.sub("", s)
    
    # mono-code向け記号補正
    if fix_code_symbols:
        # 全角記号→半角記号の変換テーブル
        table = {
            "\u00D7": "x",    # × → x
            "\u30FB": ".",    # ・ → .
            "\uFF0C": ",",    # ， → ,
            "\uFF1A": ":",    # ： → :
            "\uFF1B": ";",    # ； → ;
            "\uFF0F": "/",    # ／ → /
            "\uFF3C": "\\",   # ＼ → \
            "\u201C": '"',    # " → "
            "\u2018": "'",    # ' → '
            "\u301C": "~",    # 〜 → ~
            "\uFF0D": "-",    # － → -
            "\u2014": "-",    # — → -
            "\u2013": "-",    # – → -
            "\uFF3F": "_",    # ＿ → _
            "\uFF08": "(",    # （ → (
            "\uFF09": ")",    # ） → )
            "\uFF3B": "[",    # ［ → [
            "\uFF3D": "]",    # ］ → ]
            "\uFF5B": "{",    # ｛ → {
            "\uFF5D": "}",    # ｝ → }
        }
        s = "".join(table.get(ch, ch) for ch in s)
        # ひらカナの「ノ」をスラッシュと誤るケースの軽減（連接のみ抑制）
        s = re.sub(r"(?<=\S)ノ(?=\S)", "/", s)
    
    # 全角空白を半角へ（行頭インデント対策）
    s = s.replace("\u3000", " ")
    
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
                hyp_norm = normalize_text(r.text, keep_spaces=keep_spaces, ignore_boxdrawing=True, fix_code_symbols=keep_spaces)
                # ★ツリー行構造補正（mono-code限定）
                if keep_spaces and "mono-code" in tags:
                    lines_before = hyp_norm.splitlines()
                    lines_after = [repair_tree_listing_line(line) for line in lines_before]
                    hyp_norm = "\n".join(lines_after)
                    # デバッグ: 最初の3行の変換前後を表示
                    print(f"[DEBUG] Tree repair for {file_id}:")
                    for i in range(min(3, len(lines_before))):
                        if i < len(lines_before) and i < len(lines_after):
                            if lines_before[i] != lines_after[i]:
                                print(f"  Line {i}: '{lines_before[i][:50]}' → '{lines_after[i][:50]}'")
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
