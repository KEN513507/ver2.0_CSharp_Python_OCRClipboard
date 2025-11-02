# 🖼️ Custom OCR Clipboard App (Blueprint)

このディレクトリは、将来 Windows 向けのカスタム OCR Clipboard アプリを作るための **設計ノート** です。まだソースコードは存在せず、「どんな機能を入れるか」「どんなフォルダ構成にするか」だけを整理しています。

## 現在の状態
```
ocr_clipboard_app/
└── BLUEPRINT.md   (この設計ノートのみ)
```

- 実装ファイル（capture.py / ocr.py など）は未作成です。
- 依存関係や CI 設定もまだ導入していません。
- 実装が始まるときは、下記「想定ディレクトリ構成」と「TODO ロードマップ」を参考に準備を進めてください。

## 想定ディレクトリ構成（計画）
```
ocr_clipboard_app/
├── capture.py          # Tkinter + MSS による範囲選択とキャプチャ
├── ocr.py              # PaddleOCR ベースの OCR パイプライン
├── test_ocr.py         # 手動動作確認用スクリプト
├── fonts/              # NotoSansCJKjp など OCR 可視化用フォント
├── images/             # デバッグ用キャプチャ保存ディレクトリ
├── requirements.txt    # 依存パッケージ
└── tests/              # 自動テスト（将来的に追加）
```

## 実装方針（ハイライト）
- **OCR エンジン**: PaddleOCR（日本語モデル）を前提に利用する。
- **DPI 対応**: Display 1 で DPI 100% に固定し、複数ディスプレイ対応は追加課題にする。
- **範囲選択**: Tkinter の半透明オーバーレイ + MSS/PIL で画面を切り取る。
- **クリップボード処理**: 読み取った文字を自動コピーし、必要なら自信度や可視化も表示する。
- **自動化**: コマンド引数でバッチ処理や Human-in-the-Loop（人の確認を挟むワークフロー）にも対応できるようにする。

## TODO ロードマップ
1. `requirements.txt` の作成と依存ライブラリ（paddleocr, mss など）の確定。
2. `capture.py` と `ocr.py` の MVP 実装。
3. クリップボード出力・ログ記録などの運用機能を追加。
4. `tests/` ディレクトリでユニットテスト／統合テストを整備。
5. GitHub Actions などの CI/CD を導入。

## 関連ドキュメント
- ルート `README.md`: プロジェクト全体と C# × Python IPC の概要。
- `ocr_app/CLI_SAMPLE_GUIDE.md`: PaddleOCR を使った検証用 CLI サンプル。
- `ocr_sharp/OPERATIONS_GUIDE.md`: DPI 対応済みの Python 実運用クライアント。

将来的に実装が進んだら、本 README をアップデートして利用者向けの手順書へ昇格させてください。
