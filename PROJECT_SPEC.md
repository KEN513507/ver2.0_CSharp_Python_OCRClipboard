# OCR Clipboard v2.0 開発仕様（Windows.Media.Ocr）

## 0. Summary

- **対象構成**: C# (.NET 8) + Windows.Media.Ocr のみ
- **除外**: Python ワーカー / PaddleOCR / IPC（`start_ocr_worker.cmd` は歴史的遺産）
- **主目的**: Display 1 上で矩形選択 → OCR → クリップボードをサブ秒で完結させる常駐アプリ

---

## 1. 要件

### 1.1 機能要件（Functional）

| ID | 要件 | 詳細 / 根拠 | 状態 | 担当モジュール |
|----|------|-------------|------|----------------|
| F-1 | 常駐 | 起動後トレイ常駐・高速状態維持 | 未実装 | OCRClipboard.App (NotifyIcon) |
| F-2 | ホットキー | グローバルホットキーで矩形選択→OCR→クリップボード | 未実装 | OCRClipboard.App (RegisterHotKey) |
| F-3 | 速度 | 2回目以降 `proc_total` < 1s | 達成 (実測 0.3s) | PerfLogger + Program.cs |
| F-4 | クリップボード | OCR成功時のみ自動コピー | 達成 | Program.cs (`TrySetClipboardText`) |
| F-5 | 終了手段 | トレイメニュー等で安全終了 | 未実装 | NotifyIcon メニュー |
| F-6 | 品質判定 | Levenshtein ≤ min(⌈0.25×|text|⌉,20) ∧ mean_conf ≥ 0.7 | ロジックのみ | Quality/OcrQualityEvaluator → Program.cs へ配線要 |

### 1.2 非機能要件（Non-Functional）

| ID | 要件 | 詳細 | 状態 | 備考 |
|----|------|------|------|------|
| NF-1 | サブ秒応答 | 冷スタート不問。proc_total <1s を維持 | 達成 | `[PERF]` ログ証跡あり |
| NF-2 | 対応環境 | Display 1 / DPI100% / Windows 10 1809+ | 達成 | ドキュメント明記 & 実測確認 |
| NF-3 | バイナリサイズ | Self-contained バイナリ < 20MB | 未測定 | `dotnet publish` 要実施 |
| NF-4 | メモリ常駐量 | 100MB 未満 | 未測定 | 実測してドキュメントに追記 |

### 1.3 非対応範囲

- Display 2 以降の座標補正 / DPI 125%+ / 仮想デスクトップ
- GPU / PaddleOCR 等の大型モデル
- Python ワーカー連携（`start_ocr_worker.cmd` は利用しない）

---

## 2. アーキテクチャ

```
[User]
  └─ (予定) Ctrl+Shift+O  ──────────────┐
                                         ▼
[OCRClipboard.App]
  ├─ OverlayWindow (WPF) …… Display1 / DPI100% の矩形選択 UI
  ├─ WindowsMediaOcrEngine …… OCR 実行 (Windows.Media.Ocr)
  ├─ PerfLogger ………………… [PERF]/[OCR]/ログ整形
  ├─ QualityConfig / Evaluator … 品質閾値とヒューリスティック
  └─ Clipboard helper ………  STA スレッドでテキスト書き込み

補助プロジェクト: Infra / Ocr / Quality / Worker (C#)
テスト: tests/OCRClipboard.Tests（Fast Only, SlowOCR 雛形）
```

`start_ocr_worker.cmd` 等、Python を前提としたファイルは「Legacy（触らない）」として残置しています。

---

## 3. 実装マトリクス

| コンポーネント | 主ファイル | 役割 | メモ |
|----------------|------------|------|------|
| `OCRClipboard.App` | `Program.cs`, `OverlayWindow.xaml.cs` | UI／エントリーポイント | 常駐・HK 未実装、ログはサブ秒達成 |
| `Ocr` | `WindowsMediaOcrEngine.cs`, `OcrResult.cs` | OCR ライブラリ | Timings 付き結果を返す |
| `Quality` | `OcrQualityEvaluator.cs`, `QualityConfig.cs` | 品質ヒューリスティック | CER/Band 設定を保持。Program.cs 未配線 |
| `Infra` | `PerfLogger.cs` | 性能ログ出力 | `[PERF]` `[OCR]` 形式を統一 |
| `Worker` | `Worker.cs` | JSON-over-stdin 実装 | テストで使用（FakeOcrEngine利用） |
| `tests/OCRClipboard.Tests` | `*.cs` | xUnit テスト | SlowOCR はテンプレート (Skip) |
| `scripts/run_dev_checks.ps1` | — | restore → build → format → test → typos | `check` エイリアス経由で実行 |
| Legacy (触らない) | `start_ocr_worker.cmd`, `src/python/**` | 旧 PaddleOCR 資産 | 現行ビルド対象外 |

---

## 4. 運用・検証

- `[タイミング分析]` / `[PERF]` ログ … `proc_total`、`user`、`grab` などを監視
- `[OCR]` / `[CLIPBOARD]` … フラグメント数とコピー成否を確認
- ログ保存先 … `src/csharp/OCRClipboard.App/logs/`
- `docs/TECHNICAL_LIMITS.md` に Windows.Media.Ocr の性能ベンチマークを掲載
- `scripts/run_dev_checks.ps1` を CI とローカルの両方で使用

---

## 5. 今後のロードマップ

1. NotifyIcon 常駐化・RegisterHotKey 対応（F-1/F-2/F-5）
2. CER/Accuracy を `Program.cs` に接続し `[QUALITY]` ログを出力（F-6）
3. `dotnet publish` + 実行時計測による NF-3/NF-4 の数値化
4. SlowOCR 実機テストの実装および self-hosted runner 検討

---

## 6. ドキュメント参照先

- `README.md` …… 実装ステータスと実行手順
- `docs/CI_CD_STRATEGY.md` …… build / release ワークフロー詳細
- `docs/TECHNICAL_LIMITS.md` …… OCR の性能・制約
- `docs/BENCHMARK.md`, `docs/DEBUG_MODE.md` …… 追加情報
- `salvage/` …… 旧 PaddleOCR 資産（参考資料のみ）

---

## 7. 変更履歴

- 2025-11-01: Windows.Media.Ocr 版仕様として再定義、Python 依存を非対象に明記
