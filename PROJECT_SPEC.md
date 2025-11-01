# OCR Clipboard v2.0 開発仕様（Windows.Media.Ocr版）

## 概要
- **構成**: C#単体（.NET 8、Windows.Media.Ocr）
- **性能目標**: OCR処理100ms以内（2回目以降）
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
    ├─ WindowsMediaOcrEngine → OCR実行（100ms）
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
| NF-1 | OCR処理時間 < 200ms | ✅ 72-155ms |
| NF-2 | 言語: 日本語優先、英語フォールバック | ✅ lang='ja' |
| NF-3 | DPI 100%専用 | ✅ 固定 |
| NF-4 | Display 1専用 | ✅ MONITOR_DEFAULTTOPRIMARY |

---

## 運用ログ形式

```
[OCR] Engine=Windows.Media.Ocr lang='ja'
[PERF] capture=3716ms convert=115ms ocr=72ms total=4000ms
[OCR] n_fragments=16 mean_conf=1.00 sample="をな帑ｿ｡鬆ｼ蠎ｦ100%と表示される・オ"
[CLIPBOARD] copied=true length=18
```
                       ▲                 ▲
                       │                 │
                   D1 設定/プリセット   D2 テストケース(期待語句/正解) ← テスト時のみ使用
```

#### 各プロセスの要点と10秒制約配分（上限例）

- **P2/P3**（モニタ特定・選択UI）：~1.0s（UI描画は即時）
- **P4/P5**（キャプチャ・前処理）：~0.8s（GPU→GPUクロップ、2×拡大/Grayなど）
- **P6/P7**（IPC＋推論）：~7.5s（モデル初期化はウォームアップ、以降キャッシュ）
- **P8**（正規化/半全角/ダッシュ統一）：~0.3s
- **P9**（出力＋ログ）：~0.2s
  ※ 合計 9.8s 以内を目安。超過時はデグレード（小モデル/解像度下げ）へフェイルセーフ。

---

# 追加仕様・注意点
- DFD/ER図・品質基準・テストケースは本ファイルに随時追記
- 仕様変更・課題・運用ルールもここに記載
