# 🖼️ Custom OCR Clipboard App (for Windows)

**現状のディレクトリツリー（2025-10-29時点）**

```
ocr_clipboard_app/
├── README.md
```

※現時点では `README.md` のみ存在しています。

---

## 状況・今後の作業

- サンプルディレクトリ構成（README記載）は以下の通り：
  - capture.py, ocr.py, test_ocr.py, fonts/, images/, requirements.txt, .github/workflows/ci.yml など
- しかし、現状はまだ各実装ファイル・サブディレクトリは未作成です。
- 実装開始前の雛形状態です。
- 今後、README記載の構成に沿って capture.py, ocr.py, test_ocr.py などを追加していく必要があります。
- 依存パッケージ・CI/CD・カスタマイズ方針はREADMEに明記済み。

---

## 参考: README記載のFeatures

- PaddleOCR日本語対応
- Display 1専用・DPI 100%固定
- Tkinter範囲選択
- MSS/PILキャプチャ
- クリップボード自動コピー
- 信頼度・可視化
- CLI/自動化
- Human-in-the-Loop拡張性

---

## 次のステップ

1. README記載の構成に従い、各Pythonファイル・サブディレクトリを新規作成
2. requirements.txtを追加し、依存パッケージを管理
3. 実装・テスト・CI/CDの整備

---

現状は「README.mdのみ」の初期状態です。今後のファイル追加・実装方針はREADME記載の構成・Featuresに従って進めてください。

**A DPI-aware, high-quality, fast OCR app for Windows.**  
This app allows you to select a region of the screen, perform OCR using PaddleOCR (Japanese), and copy the recognized text to clipboard **automatically**.  
Supports display scaling quirks, runs on **Display 1 only**, and is customizable for your needs.

---

## 🚀 Features

- ✅ Uses **PaddleOCR** (Japanese) for accurate recognition
- ✅ Works on **Display 1 only**, DPI scaling fixed at 100% (no pixel drift!)
- ✅ Mouse-based region selection with **Tkinter**
- ✅ Fast capture using **MSS** or fallback with **PIL**
- ✅ Auto copy result to clipboard
- ✅ OCR confidence score & visualization (optional)
- ✅ CLI or script-based automation
- ✅ Future-ready for Human-in-the-Loop workflows

---

## 📁 Directory Structure

```
ocr_clipboard_app/
├── capture.py # Region selection, screen capture (Tkinter + MSS)
├── ocr.py # OCR pipeline using PaddleOCR
├── test_ocr.py # Test script for OCR with clipboard
├── fonts/ # Japanese fonts (e.g. NotoSansCJKjp-Regular.otf)
├── images/ # For saving screenshots / OCR output
├── requirements.txt # All dependencies
├── README.md # You're reading this
└── .github/
    └── workflows/
        └── ci.yml # GitHub Actions for lint/test (CI)
```

---

## 📦 Installation

### 1. Clone this repo

```bash
git clone https://github.com/YOUR_USERNAME/ocr_clipboard_app.git
cd ocr_clipboard_app
```

2. Create virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

🔧 If you use Windows, also install Tesseract if you plan to try alternate engines.
📐 Ensure Display 1 is DPI 100% for perfect pixel capture.

---

## 🧪 Usage
Run the OCR app and copy result to clipboard:
```bash
python test_ocr.py
```

- A window will prompt you to select a region on Display 1.
- OCR is performed.
- Text is copied to clipboard.
- (Optional) Saved annotated image in /images/result.jpg

---

## ✍️ Customization Tips
- Change OCR model: ocr.py → modify PaddleOCR(...)
- Visual debug: Enable result image output
- OCR region auto-detect? Add detection layer before capture.py

---

## ⚙️ CI/CD (with GitHub Actions)
.github/workflows/ci.yml
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run Tests
        run: |
          python -m unittest discover tests
```
You can add test cases under tests/ directory later.

---

## ✅ Requirements
- paddleocr
- paddlepaddle
- pyperclip
- opencv-python
- mss
- pyautogui
- Pillow
- tk

---

## 🧠 Why This App?

Windows Snipping Tool is nice — but it can't:
- Customize the OCR pipeline
- Modify post-processing rules
- Automatically copy cleaned text to clipboard
- Run in batch/CLI/headless mode

This app can. It’s built for devs, researchers, and power users who want full control over screen-based OCR workflows.

---

## 📖 License

MIT License.
