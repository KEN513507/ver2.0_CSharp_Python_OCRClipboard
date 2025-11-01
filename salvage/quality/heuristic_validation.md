# OCR品質判定ヒューリスティック（スコアレスOCR対応）

## 課題
Windows.Media.Ocr や軽量OCRは**信頼度スコアを返さない**場合が多い。

## 解法
**文字列距離 + 記号比率 + 長さ比** で最低限の品質をガード。

## 判定ロジック

### 1. 編集距離（Levenshtein）
```python
from Levenshtian import distance

def is_acceptable_edit(ocr_text: str, reference: str) -> bool:
    """誤差が原文の25%以内 かつ 20文字以内なら許容"""
    dist = distance(ocr_text, reference)
    max_rel = len(reference) * 0.25
    max_abs = 20
    return dist <= min(max_rel, max_abs)
```

### 2. 記号/特殊文字の比率ガード
```python
import re

def has_excessive_symbols(text: str, max_ratio=0.3) -> bool:
    """記号が30%超なら誤検出の可能性"""
    symbols = len(re.findall(r'[^\w\s]', text))
    return symbols / max(len(text), 1) > max_ratio
```

### 3. 長さ比チェック
```python
def length_ratio_ok(ocr_text: str, reference: str, min_ratio=0.5) -> bool:
    """OCR結果が原文の50%未満なら不完全"""
    return len(ocr_text) / max(len(reference), 1) >= min_ratio
```

### 4. 正規化（NFKC + 大文字小文字統一）
```python
import unicodedata

def normalize(text: str, ignore_case=True) -> str:
    """判定前に統一処理"""
    text = unicodedata.normalize("NFKC", text)
    if ignore_case:
        text = text.lower()
    return text
```

## 統合判定
```python
def validate_ocr_result(ocr_text: str, reference: str) -> tuple[bool, str]:
    """品質OK → (True, ""), NG → (False, "理由")"""
    ocr_norm = normalize(ocr_text)
    ref_norm = normalize(reference)
    
    if has_excessive_symbols(ocr_norm):
        return False, "記号比率が異常"
    if not length_ratio_ok(ocr_norm, ref_norm):
        return False, "長さが不足"
    if not is_acceptable_edit(ocr_norm, ref_norm):
        return False, f"編集距離が閾値超過: {distance(ocr_norm, ref_norm)}"
    
    return True, ""
```

## 環境変数での調整
```python
import os

MAX_REL_EDIT = float(os.getenv("OCR_MAX_REL_EDIT", "0.25"))
MAX_ABS_EDIT = int(os.getenv("OCR_MAX_ABS_EDIT", "20"))
MAX_SYMBOL_RATIO = float(os.getenv("OCR_MAX_SYMBOL_RATIO", "0.3"))
MIN_LENGTH_RATIO = float(os.getenv("OCR_MIN_LENGTH_RATIO", "0.5"))
```

## C# 移植例
```csharp
using Fastenshtein;

public static bool IsAcceptableEdit(string ocrText, string reference)
{
    var dist = Levenshtein.Distance(ocrText, reference);
    var maxRel = reference.Length * 0.25;
    var maxAbs = 20;
    return dist <= Math.Min(maxRel, maxAbs);
}
```

## 適用範囲
- Windows.Media.Ocr（スコアなし）
- Tesseract（スコアが不安定）
- 軽量クラウドOCR（低精度API）
- レシート・名刺など**定型テキストの検証**
