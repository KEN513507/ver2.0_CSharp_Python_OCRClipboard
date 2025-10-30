いいドキュメントじゃねぇか…「C#とPythonでOCR連携」とか、異種格闘技戦かよ。だが、今のままじゃ**強いけど野暮ったい**。全体の構成や表現をちょっと引き締めて、現場で通じる**最新のベストプラクティスっぽい雰囲気**に整えてやるよ。

---

````markdown
# 🧠 Copilot Instructions for `ver2_0_CSharp_Python_OCRClipboard`

## 📌 Overview
このリポジトリは、**C#とPythonによるOCR連携アプリケーション**の統合プロジェクトです。構成は以下の通り：

- `src/csharp/OCRClipboard.App`：  
  C# コンソールアプリ。DTO定義と Python ワーカーとの IPC クライアント。
  
- `src/csharp/OCRClipboard.Overlay`：  
  WPF製オーバーレイUI。矩形選択により画面キャプチャ（Display 1限定）。
  
- `src/python/ocr_worker`：  
  PythonベースのOCRエンジン。DTO解析、ロジック処理、結果返却。
  
- `ocr_app/`, `ocr_sharp/`：  
  DPIスケーリング/座標補正込みのOCR検証アプリ。

---

## 📡 Architecture / Data Flow

- C# アプリが **Pythonワーカーを JSON-over-stdio IPC** で起動・接続
- DTO（データ転送オブジェクト）は **C# ↔ Python でミラー定義**
- OCR 結果は期待されるテキストと比較し、**信頼度しきい値で判定**
- 全ログはファイル出力（OCR精度・差分検証用）

---

## 🛠 Development & Testing

### 🔧 セットアップ
- Python 依存インストール（各ディレクトリ）：
  ```bash
  pip install -r requirements.txt
````

* C# ビルド・実行：

  ```pwsh
  dotnet run --project src/csharp/OCRClipboard.App
  ```

* OCRテスト用 Python スクリプト：

  ```bash
  python ocr_app/main.py
  python ocr_sharp/main.py
  ```

* テスト実行：

  ```bash
  pytest
  ```

* 依存確認・整理：

  ```bash
  pipdeptree
  pip list --outdated
  pip freeze > requirements.txt
  ```

* CI（GitHub Actions）：

  ```bash
  gh workflow run <workflow-name>
  ```

---

## ⚠ Notes & Caveats

* **DPIスケーリングは必ず100%** に設定（Display 1 専用）
* Python 側起動時に `PYTHONPATH=src/python` を必ず指定
* `draw_ocr` 使用時は `fonts/NotoSansCJKjp-Regular.otf` を配置すること
* キャプチャ画像の出力先：`logs/debug_capture.png` 等
* DTO定義は以下で同期管理：

  * `src/csharp/OCRClipboard.App/Dto/Envelope.cs`
  * `src/python/ocr_worker/dto.py`
* 現在は **マルチディスプレイ未対応**（今後対応予定）

---

## 🗂 Reference Files

| 種別           | パス                                     |
| ------------ | -------------------------------------- |
| DTO定義        | `Dto/Envelope.cs`, `ocr_worker/dto.py` |
| DPI補正OCR     | `ocr_app/main.py`, `ocr_sharp/main.py` |
| テスト例         | `tests/`                               |
| 各モジュールREADME | 各ディレクトリ内 `README.md`                   |


> このドキュメントは **AIエージェントおよび人間の開発者**が即戦力で作業できるよう設計されています。追記・修正の要望は容赦なく投げてください。

---

## PaddleOCR API変更・エラー対応レポート（2025-10-30）

- モデルキャッシュ・ccache警告
  - PaddleOCR/PaddleXのモデルは `C:\Users\user\.paddlex\official_models\` にキャッシュされる。
  - 再ダウンロードしたい場合は該当ディレクトリを手動削除。
  - `ccache` 未インストール警告は無視してOK（高速化用）。

- FileNotFoundError: images/input.jpg
  - `ocr_app/main.py` 実行時、`images/input.jpg` が存在しないとエラー。
  - 必要なテスト画像を `ocr_app/images/input.jpg` に配置すること。

- PaddleOCR API変更対応
  - `use_gpu=False` パラメータは廃止 → 削除済み。
  - `use_angle_cls=True` → `use_textline_orientation=True` へ移行推奨（暫定で旧式も残す）。
  - `ocr.ocr(img, cls=True)` → `ocr.predict(img)` へ変更。
  - これらの修正は `ocr_app/main.py` および `src/python/ocr_worker/main.py` に反映済み。

- テスト・依存・環境
  - `paddleocr` のインストール漏れは仮想環境有効化後に `pip install paddleocr` で解決。
  - テスト実行時は `PYTHONPATH` を明示的に設定（例：`$env:PYTHONPATH="src/python"`）。
  - 依存バージョン不整合（例：networkx）は requirements.txt/in のバージョン調整で対応。

- PR・コミット
  - 上記API変更・バグ修正は `ocr-quality-eval` ブランチでコミット・PR済み。
  - PR: https://github.com/KEN513507/ver2.0_CSharp_Python_OCRClipboard/pull/1

この内容で現状のPaddleOCR連携・テスト・API互換性はクリアされています。追加のエラーや運用ルールの明文化が必要な場合はご指示ください。
```
