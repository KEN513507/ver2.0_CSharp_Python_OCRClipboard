# AI Prompt OCR v2.0: Architect Edition

[![Status](https://img.shields.io/badge/Status-OPERATIONAL-brightgreen)]()
[![Shortcuts](https://img.shields.io/badge/Shortcuts-Dual_Mode-blue)]()
[![Arch](https://img.shields.io/badge/Architecture-Core_Online-purple)]()

> **「開発の根幹を支える、最強のインフラへ。」**  
> 本ツールは単なるアプリではなく、OSと一体化したプロンプトエンジニアリング・インフラです。

---

## ⚡ 起動と合言葉 (Startup & Greeting)

ターミナルを開いた瞬間、システムが背後で牙を研いでいることを宣言します。

```text
  💠 AI Prompt OCR v2.0: ARCHITECT CORE ONLINE
  ============================================
  [STATUS]  Authentication: OK (Google Cloud ADC)
  [STATUS]  Engine: Cloud Vision / PaddleOCR Fallback
```

このメッセージは、全ての開発セッションにおいて **「準備完了」** であることを保証する合言葉です。

---

## 🚀 デュアル・モード運用 (Dual-Mode Operation)

マウスで範囲を選択するだけで、瞬時に最適なプロンプトがクリップボードに装填されます。

| ショートカット | モード | 目的 | 合成内容 |
| :--- | :--- | :--- | :--- |
| **Ctrl + Shift + E** | **Strategy** | 分析・戦略策定 | 前文 ＋ OCR結果 ＋ 後文 |
| **Ctrl + Shift + R** | **Raw Data** | 追記・ログ詳細 | OCR結果のみ (`--raw`) |

---

## 🛠️ システム構築 (System Architecture)

### 1. 認証のクリーンアップと同期
古い環境変数を排除し、Google Cloud **ADC (Application Default Credentials)** を標準採用。
```bash
# 認証の更新
gcloud auth application-default login
# 古いキーの干渉を排除（自動実行済み）
unset GOOGLE_APPLICATION_CREDENTIALS
```

### 2. インフラの即時利用
ターミナルから以下のエイリアスで直接実行も可能です。
* `ocr`: Strategy モード起動
* `ocr-raw`: Raw データモード起動

---

## 📂 主要ファイル構成

- `scan_clipboard.py`: システム本体。Google Cloud Vision と PaddleOCR のハイブリッド駆動。
- `ocr_launch.sh`: システム全体を束ねる起動ラッパー。
- `config_gui.py`: プロンプト（人格）編集用GUI。
- `PROJECT_SPEC.md`: 詳細な設計仕様とLeveshtein距離ベースの品質基準。

---
**Updated: 2026-03-31 | Architect Core Online Mode Enabled**
