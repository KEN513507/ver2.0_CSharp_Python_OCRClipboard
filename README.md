
# AI Prompt OCR v2.0: Architect Edition

[![Status](https://img.shields.io/badge/Status-COMPLETE-brightgreen)]()
[![Shortcuts](https://img.shields.io/badge/Shortcuts-Dual_Mode-blue)]()

---

## 🚀 デュアル・モード運用 (Dual-Mode Operation)

対話のフェーズに合わせて、2つの起動オプションを使い分けます。

| ショートカット | モード | 目的 | 合成内容 |
| :--- | :--- | :--- | :--- |
| **Ctrl + Shift + E** | **Strategy** | 初回分析・戦略策定 | 前文 ＋ OCR結果 ＋ 後文 |
| **Ctrl + Shift + R** | **Raw Data** | 追記・ログ詳細調査 | OCR結果のみ (`--raw`) |

---

## 🧠 設計思想 (Architect Logic)

  個人の秘伝プロンプトを保持したまま、GitHubへはダミー設定のみを公開する「完全秘匿運用」を実現。

---

## 🛠️ クイックセットアップ

### 1. 依存関係の復元
```bash
python3 -m venv .venv-ocr27
./.venv-ocr27/bin/pip install -r requirements.txt
gcloud auth application-default login
```

### 2. 人格のカスタマイズ
`./.venv-ocr27/bin/python config_gui.py` を起動し、前文・後文を設定・保存してください。

---

## 📂 主要ファイル構成

- `scan_clipboard.py`: システム本体。引数 `--raw` により挙動を切り替え。
- `config_gui.py`: プロンプト編集用GUI。
- `ocr_dashboard.py`: 統合管理パネル。
- `PROJECT_COMPLETE.txt`: 運用・保守マニュアル。

---
**Finalized: 2026-03-22 | Operational Excellence Mode Enabled**
EOF
```

---

### 🧠 アーキテクトからの最終確認



* **追加点**: 運用効率を最大化する「デュアル・モード」の比較表をトップに配置しました。
* **削除点**: 開発中のTODOや、冗長な「概要」を排除し、マニュアルとしての機能性を高めました。

