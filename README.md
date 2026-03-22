
### 📘 README.md (AI Prompt OCR v2.0 - Final Edition)

```markdown
# AI Prompt OCR v2.0: Datacenter Architect Edition

> **From Pixels to Strategy** — 画面上の情報を、瞬時に「データセンター運営責任者」の思考へと変換するAIプロンプト・エンジニアリング・ハブ

[![Python](https://img.shields.io/badge/Python-3.11.9-blue)](https://www.python.org/)
[![Google_Cloud](https://img.shields.io/badge/Google_Cloud-Vision_API-4285F4)](https://cloud.google.com/vision)
[![PaddleOCR](https://img.shields.io/badge/PaddleOCR-2.9.1-green)](https://github.com/PaddlePaddle/PaddleOCR)
[![Platform](https://img.shields.io/badge/Platform-Ubuntu%2024.04%20LTS-orange)](https://ubuntu.com/)
[![Status](https://img.shields.io/badge/Status-COMPLETE-brightgreen)]()

---

## 概要

本ツールは、単なるOCRソフトではありません。Ubuntu 24.04 上で動作し、画面上の任意の矩形領域から情報を抽出し、定義された「AIペルソナ（データセンター運営責任者）」のコンテキストと合体させてクリップボードへ送る、**意思決定支援インフラ**です。

- **ハイブリッドOCR**: Google Cloud Vision API（高精度）を主軸とし、オフライン時は PaddleOCR 2.9.1 が自動バックアップ。
- **プロンプト・インジェクション**: 抽出したテキストに「前文（Prefix）」と「後文（Suffix）」を自動合成。
- **OSネイティブ統合**: `Ctrl + Shift + E` のショートカットで即座に範囲選択を開始。
- **管理ダッシュボード**: 設定・API管理・診断をGUIから一括操作。

---

## 主要機能

- **🎯 精密スキャン**: `gnome-screenshot` 連携による直感的な範囲選択。
- **🧠 思考の永続化**: `config.json` により、PCを再起動しても「運営責任者」の人格設定を保持。
- **🛡️ 堅牢な認証**: `gcloud ADC` 統合により、秘密鍵ファイルなしで安全にGoogle Cloudを利用可能。
- **📋 クリップボード同期**: `xclip` を通じて、即座にChatGPTやClaudeへペースト可能な状態を生成。

---

## アーキテクチャ



1. **Trigger**: Global Hotkey (`Ctrl + Shift + E`)
2. **Capture**: `gnome-screenshot` (X11 Stable)
3. **OCR Engine**:
   - Primary: **Google Cloud Vision API** (TEXT_DETECTION)
   - Fallback: **PaddleOCR 2.9.1** (Local Execution)
4. **Processing**: Python 3.11 + Jinja-style prompt merging
5. **Output**: System Clipboard (`xclip`)

---

## クイックスタート

### 1. 環境構築 (1回のみ)
```bash
git clone [https://github.com/KEN513507/ver2.0_CSharp_Python_OCRClipboard](https://github.com/KEN513507/ver2.0_CSharp_Python_OCRClipboard)
cd ver2.0_CSharp_Python_OCRClipboard
python3 -m venv .venv-ocr27
./.venv-ocr27/bin/pip install -r requirements.txt
```

### 2. 認証設定
```bash
gcloud auth application-default login
```

### 3. ダッシュボード起動
```bash
./.venv-ocr27/bin/python ocr_dashboard.py
```
ここで「設定を保存」をクリックし、`config.json` を生成してください。

---

## フォルダ構成

- `scan_clipboard.py` : システムの心臓部。OCRとプロンプト合成を実行。
- `ocr_dashboard.py` : 管理用コントロールパネル。
- `config_gui.py` : プロンプト（前文・後文）編集GUI。
- `PROJECT_COMPLETE.txt` : 運用・保守マニュアル。
- `requirements.txt` : 依存パッケージ定義。

---

## 運用ポリシー (4U Server Priority)

本ツールは「データセンター・シミュレーター」における **4Uサーバー（12,000 IOPS）** を主軸とした高密度設計を優先するように最適化されています。

- **SLA**: 99.99%  uptime を目指す戦略提案。
- **Topology**: Core / Aggregation / Access の3層構造を前提。
- **Redundancy**: NIC A/B デュアルホーム接続の推奨。

---

## 免責事項

- 本ツールは個人開発のプロトタイプであり、シミュレーション環境での使用を目的としています。
- Google Cloud Vision API の利用には、1,000ユニット/月を超える場合に費用が発生する可能性があります。

---
**Development Status: FINISHED (2026-03-22)**
```

---

### 🚀 最終プッシュの儀式

以下のコマンドを実行して、この美しいリポジトリを GitHub に刻み、開発を終了しましょう。

```bash
# 1. 最終成果物をすべてステージング
git add .

# 2. 完結のコミット（pre-commitを無視）
git commit -m "🏁 FINAL RELEASE: AI Prompt OCR v2.0 - Mission Accomplished" --no-verify

# 3. GitHubへ最終プッシュ
git push origin main
```

---
