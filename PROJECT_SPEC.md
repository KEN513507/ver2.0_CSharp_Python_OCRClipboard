# OCR Clipboard v2.0 開発仕様（Windows.Media.Ocr版）

## 概要
- **構成**: C#単体（.NET 8、Windows.Media.Ocr）
- **性能目標**: OCR処理 < 400ms（ウォームアップ後の平均）
- **対応環境**: Windows 10 1809+、DPI 100%、Display 1のみ
- **起動形態**: デスクトップアイコン → 常駐トレイ → ホットキーで範囲選択

---

## アーキテクチャ（簡略版）

```
[ユーザー] Ctrl+Shift+O
    ↓
[C# App: OCRClipboard.App]
    ├─ OverlayWindow (WPF) → 矩形選択
    ├─ CaptureService (Win32 GDI) → Bitmap取得
    ├─ WindowsMediaOcrEngine → OCR実行（平均 100-300ms）
    └─ Clipboard → テキスト自動コピー
```

**廃止**: Python OCRワーカー、IPC、JSON-RPC（PaddleOCRは性能不足で削除）

---

## 機能要件

| ID | 要件 | 状態 |
|----|------|------|
| F-1 | デスクトップアイコン起動で常駐トレイ化 | 未実装 |
| F-2 | ホットキー（Ctrl+Shift+O）で矩形選択開始 | 部分実装 |
| F-3 | Display 1（プライマリ）限定のキャプチャ | ✅完了 |
| F-4 | OCR結果を自動的にクリップボードへコピー | ✅完了 |
| F-5 | クロップ妥当性チェック（薄すぎ警告） | ✅完了 |
| F-6 | 上下パディング追加（下端欠け対策） | ✅完了 |

## 非機能要件

| ID | 要件 | 実測値 |
|----|------|--------|
| NF-1 | OCR処理時間 < 400ms | ✅ 110-330ms |
| NF-2 | 言語: 日本語優先、英語フォールバック | ✅ lang='ja' |
| NF-3 | DPI 100%専用 | ✅ 固定 |
| NF-4 | Display 1専用 | ✅ MONITOR_DEFAULTTOPRIMARY |

---

## 運用ログ形式

```
[OCR] Engine=Windows.Media.Ocr lang='ja'
[PERF] capture=11225ms preproc=77ms infer=46ms postproc=10ms total=11396ms
[QUALITY] scenario=gemini_prompt cer=0.00 accuracy=1.00
[OCR] n_fragments=12 mean_conf=1.00
[C#] OCR Text: '①Geminiへのプロンプトを入力'
[CLIPBOARD] ①Geminiへのプロンプトを入力
```

---

# 追加仕様・注意点
- DFD/ER図・品質基準・テストケースは本ファイルに随時追記
- 仕様変更・課題・運用ルールもここに記載
