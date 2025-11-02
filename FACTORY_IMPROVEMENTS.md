# OCR Test Set Factory Line - Improvements Applied

## Production Line Status: OPERATIONAL

All scripts converted to English and hardened for production use.

---

## Improvements Implemented

### 1. Font Fallback Warning
**Location:** `tools/generate_images.py`

```python
def pick_font(candidates, size: int):
    for name in candidates:
        for suffix in (".ttf", ".ttc", ""):
            try:
                return ImageFont.truetype(name + suffix, size)
            except OSError:
                continue
    # WARNING: Font not found, using default
    print(f"[WARN] Font fallback: {candidates} -> default font", file=sys.stderr)
    return DEFAULT_FONT
```

**Impact:** Prevents silent OCR scoring distortion due to missing fonts.

---

### 2. Strict Tag Parsing
**Location:** `tools/generate_images.py`

```python
def resolve_font(lang: str, tags: str, size: int):
    # Parse tags strictly by delimiter
    tag_list = tags.split("-")
    if "mono" in tag_list and "code" in tag_list:
        families = EN_MONO if lang == "EN" else JP_MONO
    else:
        families = JP_FONTS
    return pick_font(families, size)
```

**Impact:** Avoids false matches when tag composition expands in future sets.

---

### 3. Tilt Angle Variation Support
**Location:** `tools/generate_images.py`

```python
import re

def calc_style(lang: str, tags: str):
    # Extract tilt angle: tilt2, tilt5, tilt10, etc.
    tilt_match = re.search(r"tilt(\d+)", tags)
    tilt_angle = float(tilt_match.group(1)) if tilt_match else 0.0
    
    # ... other style processing ...
    
    return bg, fg, font_size, line_spacing, invert, tilt_angle

def draw_image(...):
    # ...
    if tilt_angle != 0:
        img = img.rotate(tilt_angle, expand=True, fillcolor=bg)
```

**Impact:** Ready for set2/set3 with variable rotation angles.

---

### 4. Data Quality Checks
**Location:** `tools/build_manifest.py`

```python
def build_manifest(root: str, out_path: str):
    # ...
    for txt in txt_files:
        text = txt.read_text(encoding="utf-8", errors="ignore")
        
        # Quality check: flag suspiciously short text
        if len(text.strip("\n")) <= 5:
            print(f"[WARN] Suspiciously short text: {txt.name} ({len(text)} chars)", 
                  file=sys.stderr)
        
        rows.append({...})
```

**Impact:** Catches corrupted/truncated ground truth files before image generation.

---

## Future Enhancements (TODO)

### 5. Automated Regression Testing
**Recommendation:** Add OCR evaluation hook to pipeline

```powershell
# In build_set1.ps1 - final step
Write-Host "4) Quality validation" -ForegroundColor Cyan
python tests/scripts/run_polarity_batch.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Error "OCR regression detected - score degradation"
    exit $LASTEXITCODE
}
```

**Impact:** CI-level protection against OCR engine regression.

---

## Architecture Recommendation

### Separate Test Asset Repository

Current structure mixes production code with test assets.

**Proposed split:**
```
Repository A: ver2_0_CSharp_Python_OCRClipboard
  - Source code (C#, Python)
  - Application logic
  - Unit tests

Repository B: OCR_TestAssets
  - tools/ (extract_texts, generate_images, etc.)
  - test_images/set1/
  - test_images/set2/
  - evaluation scripts
  - benchmark datasets
```

**Benefits:**
- Test assets are "sacred" - isolated versioning
- Prevents accidental corruption during refactoring
- Independent release cycles
- Easier to share datasets across projects

---

## Production Line Summary

| Component            | Status | Notes                          |
| -------------------- | ------ | ------------------------------ |
| extract_texts.py     | READY  | English, bilingual regex       |
| build_manifest.py    | READY  | Quality checks added           |
| generate_images.py   | READY  | Font warnings, tilt variants   |
| build_set1.ps1       | READY  | English output messages        |
| Regression testing   | TODO   | Add to pipeline                |
| Repository split     | TODO   | Isolate test assets            |

---

## Next Steps

### Set 2 Requirements
- English text + code samples
- Mixed language documents
- Handwriting-style noise injection
- Rotations: tilt5, tilt10
- Compression artifacts simulation

The factory line is ready. Keep it running.
