import tkinter as tk
import subprocess
import webbrowser
import os
from pathlib import Path

# パス設定
PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = PROJECT_ROOT / ".venv-ocr27/bin/python"
CONFIG_GUI = PROJECT_ROOT / "config_gui.py"
SCAN_SCRIPT = PROJECT_ROOT / "scan_clipboard.py"

def run_settings():
    subprocess.Popen([str(PYTHON_EXE), str(CONFIG_GUI)])

def run_ocr():
    # 動作確認用に手動実行ボタン
    subprocess.Popen([str(PYTHON_EXE), str(SCAN_SCRIPT)])

def open_api_console():
    webbrowser.open("https://console.cloud.google.com/apis/credentials")

def exit_app():
    root.destroy()

# GUI作成
root = tk.Tk()
root.title("OCR Master Panel")
root.geometry("300x400")
root.configure(bg="#2c3e50")

# タイトル
tk.Label(root, text="AI OCR CONTROLLER", fg="white", bg="#2c3e50", font=("Arial", 12, "bold")).pack(pady=20)

# ボタン群
btn_params = {"width": 20, "font": ("Arial", 10), "pady": 10}

tk.Button(root, text="⚙️ 設定を開く", command=run_settings, **btn_params).pack(pady=5)
tk.Button(root, text="📸 OCRを手動起動", command=run_ocr, **btn_params).pack(pady=5)
tk.Button(root, text="🔗 Google API設定", command=open_api_console, **btn_params).pack(pady=5)
tk.Button(root, text="❌ パネルを閉じる", command=exit_app, bg="#e74c3c", fg="white", **btn_params).pack(pady=20)

root.mainloop()
