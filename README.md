# OCR Clipboard v2.0

> **Visual-to-Text Bridge** — 画面に見えるものをすべてテキスト化し、クリップボードへ送る汎用OCRインフラ

[![Python](https://img.shields.io/badge/Python-3.11.9-blue)](https://www.python.org/)
[![PaddleOCR](https://img.shields.io/badge/PaddleOCR-2.9.1-green)](https://github.com/PaddlePaddle/PaddleOCR)
[![.NET](https://img.shields.io/badge/.NET-8.0.125-purple)](https://dotnet.microsoft.com/)
[![Platform](https://img.shields.io/badge/Platform-Ubuntu%2024.04%20LTS-orange)](https://ubuntu.com/)
[![Test](https://img.shields.io/badge/Tests-PASS%2015%2FSKIP%201%2FFAIL%200-brightgreen)]()

---

## 概要

C# (Orchestrator) + Python (OCR Worker) の二層構成で、画面上の任意の矩形領域を選択 → OCR認識 → クリップボードへ自動コピーするデスクトップツールです。

- **ブラウザのコピー不可テキスト**（Canvas描画、React UIなど）をテキスト化
- **設定画面のIPアドレス・URLのスキャン取得**
- **ドキュメント内のコードスニペット**の素早い抽出
- ゲームUIの数値読み取り（IOPS等）

---

## 動作確認済み環境（2026-03-22）

| 項目 | 値 |
|---|---|
| OS | Ubuntu 24.04.4 LTS (Noble Numbat) |
| カーネル | 6.17.0-19-generic |
| セッション | X11 (HDMI 1920×1080) |
| Python | 3.11.9 (pyenv) |
| PaddleOCR | **2.9.1** (CPU動作・PaddlePaddle 2.6.2) |
| yomitoku | 0.12.0 |
| OpenCV | 4.11.0 |
| .NET SDK | 8.0.125 |
| クリップボード | xclip (X11) |
| CPU | Intel Core i5-4570 @ 3.20GHz |
| GPU | NVIDIA GTX 970 (OCR未使用・CPU動作) |
| RAM | 16GB |

> **備考**: PaddleOCR 3.x はi5-4570のoneDNN非対応で動作不可。2.9.1で安定動作を確認。

---

## アーキテクチャ

```
[ユーザー操作]
     │ ホットキー（未実装）/ 起動
     ▼
[C# Orchestrator]  ← Ubuntu移植作業中
  ├── 矩形選択UI (PyQt6予定)
  ├── スクリーンショット取得 (grim / scrot)
  └── JSON-over-stdio → Python Worker呼び出し
             │
             ▼
     [Python OCR Worker]  ← 動作中
       ├── PaddleOCR 2.9.1 (日本語/多言語)
       ├── yomitoku 0.12.0 (日本語特化)
       ├── refine_text (IP・URL誤認補正)
       └── 結果 → xclip → クリップボード
```

---

## クイックスタート

### Python環境セットアップ

```bash
# リポジトリクローン
git clone https://github.com/KEN513507/ver2.0_CSharp_Python_OCRClipboard
cd ver2.0_CSharp_Python_OCRClipboard

# venv作成（pyenv 3.11.9推奨）
~/.pyenv/versions/3.11.9/bin/python -m venv .venv-ocr27
source .venv-ocr27/bin/activate

# 依存インストール
pip install --upgrade pip
pip install paddlepaddle==2.6.2
pip install paddleocr==2.9.1
pip install opencv-python-headless yomitoku

# 動作確認
python -c "import cv2; import paddleocr; print('OK')"
```

### OCR Workerの直接起動（Python単体）

```bash
source .venv-ocr27/bin/activate
PYTHONPATH=src/python python src/python/ocr_worker/handler.py
```

### 全体テスト（16項目）

```bash
source .venv-ocr27/bin/activate
python tests/scripts/test_v3.py
# 期待結果: PASS:15 / SKIP:1 / FAIL:0
```

---

## フォルダ構成

```
.
├── src/
│   └── python/
│       └── ocr_worker/
│           ├── handler.py          # OCR Worker本体（JSON-over-stdio）
│           ├── capture_linux.py    # [TODO] grim連携スクリーンショット
│           └── selector_linux.py   # [TODO] PyQt6透明オーバーレイUI
├── tests/
│   └── scripts/
│       └── test_v3.py              # 総合テスト v4（16項目）
├── docs/
│   ├── DOCUMENTATION_NAV.md        # 全ドキュメントの案内図
│   └── requirements_trace_20251102.md  # 最新要件・DFD/ER（必読）
├── tools/
│   ├── paddle_warmup.py            # モデル事前ロード
│   └── visualize_ocr_results.py    # マハラノビス異常検知テスト
├── .venv-ocr27/                    # Python仮想環境（pyenv 3.11.9）
├── requirements.txt                # 依存パッケージ（pip freeze済）
└── README.md                       # 本ファイル
```

> `src/csharp/` は Ubuntu移植作業中。C# Orchestratorの再構築は次フェーズで実施予定。

---

## 品質制約

| 制約 | 基準値 | 現状 |
|---|---|---|
| OCR実行時間 | 10秒以内 | **4.73秒** ✅（2回目以降・キャッシュ済み） |
| 認識誤差 | 原文の25%以内 または20文字以内 | 測定中 |
| マハラノビス距離 | D² > 26.0 で警告 | 実装済み |
| 初回起動 | モデルDLあり | 約15秒（キャッシュ後は短縮） |

---

## 既知の問題・制限事項

| 項目 | 状況 | 対処 |
|---|---|---|
| PaddleOCR 3.x非対応 | i5-4570のoneDNN未対応でクラッシュ | **2.9.1固定** |
| GPU未使用 | GTX970のCUDAライブラリ不整合 | CPU動作で品質・速度ともに要件内 |
| C# Orchestrator | Ubuntu未移植 | 次スプリントで対応 |
| 矩形選択UI | 未実装 | PyQt6で実装予定 |
| グローバルホットキー | 未実装 | 対応予定 |
| Wayland未対応 | 現環境はX11 | grim追加済みで対応可能 |
| DPI 100%前提 | 他DPIは品質保証外 | 調査中 |

---

## Ubuntu移植ロードマップ

```
Phase 1 ✅ 完了（2026-03-22）
  └── Python環境整備（venv/PaddleOCR 2.9.1/テスト16項目全通過）

Phase 2 🔧 次スプリント
  ├── capture_linux.py  ── grim連携スクリーンショット実装
  └── selector_linux.py ── PyQt6透明オーバーレイUI実装

Phase 3 📋 予定
  └── src/csharp/ ── .NET 8.0でLinux対応Orchestratorを再構築

Phase 4 📋 予定
  └── ホットキー常駐トリガー（libinput または xdotool）
```

---

## 注意事項

- `src/python/ocr_worker/main.py` は**使用禁止**（CI/pre-commitフックで検出）
- `PYTHONPATH=src/python` を設定してPythonを起動すること
- PaddleOCRのモデルキャッシュは `~/.paddleocr/` に保存される
- `FLAGS_use_mkldnn=0` は `.bashrc` に設定済み（oneDNN無効化）
- 初回起動時はモデルDLのためネットワーク接続が必要

---

## ドキュメント参照順

1. `docs/requirements_trace_20251102.md` — 最新要件・DFD/ER・テスト観点（**必読**）
2. `PROJECT_SPEC.md` — ユーザー体験とプロセス分解（P1〜P9）
3. `docs/DOCUMENTATION_NAV.md` — 各資料への案内図

---

## 開発環境チェックリスト（本番前）

```bash
# 依存の最新化
pip list --outdated
pip freeze > requirements.txt

# テスト全通過確認
python tests/scripts/test_v3.py

# マハラノビス異常検知テスト
python tools/visualize_ocr_results.py

# Git状態確認
git log --oneline --graph -10
git status
```
