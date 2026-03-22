import tkinter as tk
from tkinter import messagebox
import json
import os
from pathlib import Path

# 🌟 実行ファイルがある場所を基準にパスを固定（これで忘れない）
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "config.json"

def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("clipboard_wrapper", {})
        except:
            pass
    return {"enabled": True, "prefix_text": "", "suffix_text": "", "timestamp_enabled": False}

def save_config():
    config_data = {
        "clipboard_wrapper": {
            "enabled": True,
            "prefix_text": prefix_text_area.get("1.0", tk.END).strip(),
            "suffix_text": suffix_text_area.get("1.0", tk.END).strip(),
            "timestamp_enabled": ts_var.get(),
            "timestamp_format": "%Y-%m-%d %H:%M:%S",
            "timestamp_position": "start",
            "debug_log": True,
            "log_level": "INFO",
            "log_file": "ocr_wrapper.log"
        }
    }
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)
    messagebox.showinfo("成功", f"記憶（設定）をディスクに刻みました！\n場所: {CONFIG_PATH}")

root = tk.Tk()
root.title("AI Prompt Engineering Configurator")
root.geometry("600x650")

tk.Label(root, text="🚀 AIプロンプト設定（永続化モード）", font=("Arial", 14, "bold")).pack(pady=10)

tk.Label(root, text="【前文】Prefix:", font=("Arial", 10, "bold")).pack(anchor="w", padx=20)
prefix_text_area = tk.Text(root, height=8, font=("Consolas", 10))
prefix_text_area.pack(padx=20, pady=5, fill=tk.X)

tk.Label(root, text="【後文】Suffix:", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=(10, 0))
suffix_text_area = tk.Text(root, height=8, font=("Consolas", 10))
suffix_text_area.pack(padx=20, pady=5, fill=tk.X)

ts_var = tk.BooleanVar()
tk.Checkbutton(root, text="タイムスタンプを付加", variable=ts_var).pack(pady=10)

# 起動時に「外部記憶」から読み込む
current_cfg = load_config()
prefix_text_area.insert("1.0", current_cfg.get("prefix_text", ""))
suffix_text_area.insert("1.0", current_cfg.get("suffix_text", ""))
ts_var.set(current_cfg.get("timestamp_enabled", False))

tk.Button(root, text="💾 設定を保存（PC再起動後も有効）", command=save_config, bg="#2E7D32", fg="white", font=("Arial", 12, "bold"), height=2).pack(pady=20)

root.mainloop()
