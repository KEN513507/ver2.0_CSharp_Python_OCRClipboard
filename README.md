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
  [STATUS]  Authentication: OK (Google Cloud ADC Secure)
  [STATUS]  Engine: Cloud Vision / PaddleOCR Fallback
```

このメッセージは、全ての開発セッションにおいて **「準備完了」** であることを保証する合言葉です。

---

## 🚀 デュアル・モード運用 (Dual-Mode Operation)

マウスで範囲を選択するだけで、瞬時に最適なプロンプトがクリップボードに装填されます。
**Super（Windows）キー** を起点にすることで、Steam等のゲーム操作中も干渉せず発動可能です。

| ショートカット | モード | 目的 | 合成内容 |
| :--- | :--- | :--- | :--- |
| **Super + Shift + X** | **Strategy** | 分析・戦略策定 | 前文 ＋ OCR結果 ＋ 後文 |
| **Super + Shift + Z** | **Raw Data** | 追記・ログ詳細 | OCR結果のみ (`--raw`) |

---

## 💻 動作環境とインフラ (Platform Infrastructure)

本システムは **Ubuntu / GNOME (X11)** 環境に特化して最適化されています。

*   **Display Server**: **X11 (Native)**
*   **Focus Management**: `xdotool` による自動フォーカス奪還（Steam/フルスクリーン対応）。
*   **Capture Engine**: `gnome-screenshot` (Area Selection)
*   **Notification**: `notify-send` によるデスクトップ通知。

### 🛡️ セキュリティと認証 (Secure ADC)
本システムは `ocr-key.json` 等のローカルキーを使用せず、Google Cloud **Application Default Credentials (ADC)** を採用しています。
認証が切れた場合は、以下のコマンドで再認可を行ってください。
```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

---

## 📂 主要ファイル構成

- `scan_clipboard.py`: システム本体。Google Cloud Vision と PaddleOCR のハイブリッド駆動。
- `ocr_launch.sh`: システム全体を束ねる起動ラッパー。通知と環境管理を司る。
- `config_gui.py`: プロンプト（人格）編集用GUI。
- `PROJECT_SPEC.md`: 詳細な設計仕様とLeveshtein距離ベースの品質基準。

---
**Updated: 2026-04-02 | Infrastructure Stabilized (Full-screen & ADC Fixed)**
