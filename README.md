# OCR Clipboard v2.0（Windows.Media.Ocr 版）

Windows デスクトップで「範囲選択 → OCR → クリップボード」を高速に行う C#/.NET 8 プロジェクトです。旧 PaddleOCR（Python）構成は撤去済みで、`salvage/` 以下に資料として保管しています。現行コードは **Windows.Media.Ocr を利用した C# 単独構成** を前提とします。

---

## 1. 実装ステータス

| 区分 | 内容 | 状態 |
|------|------|------|
| コアアプリ | `OCRClipboard.App`（WPF オーバーレイ + Windows.Media.Ocr + クリップボード） | ✅ 動作中 |
| ライブラリ | `Ocr` / `Quality` / `Infra` / `Worker` | ✅ 利用可能 |
| テスト | `tests/OCRClipboard.Tests`（xUnit Fast テスト） | ✅ 実行可 |
| 自動チェックスクリプト | `scripts/run_dev_checks.ps1` | ✅ restore → build → format → test → typos |
| Python ワーカー | `start_ocr_worker.cmd` など | ❌ **コードなし**（旧構成の残骸） |
| 常駐 / ホットキー | NotifyIcon, RegisterHotKey | ❌ 未実装 |
| 品質判定配線 | CER/Accuracy を OCR 結果に反映 | ⚠️ ロジックのみ存在（未配線） |

> **注意**: `start_ocr_worker.cmd` や `src/python/**` は現在のビルドでは利用されません。触らず残してください（歴史的資料）。

---

## 2. 合意済み要件

### 機能要件（F）

- **F-1 常駐**: トレイ常駐 & 高速状態維持（未実装）
- **F-2 ホットキー**: グローバルホットキーで矩形選択→OCR→クリップボード（未実装）
- **F-3 速度**: 2回目以降 `proc_total` < 1 秒（実測 0.3 秒前後で達成）
- **F-4 クリップボード**: OCR 成功時に自動コピー / 失敗時は未コピー（実装済み）
- **F-5 終了**: トレイメニュー等で安全に終了（未実装）
- **F-6 品質**: Levenshtein ≤ min(⌈0.25×文字数⌉, 20) かつ mean_conf ≥ 0.7（ロジックのみ）

### 非機能要件（NF）

- **NF-1**: 冷スタート除き `proc_total` < 1 秒（ログ証跡あり）
- **NF-2**: Display 1 / DPI 100% 専用（実測 OK）
- **NF-3**: 配布バイナリ < 20MB（未計測）
- **NF-4**: 常駐メモリ < 100MB（未計測）

非要件: Display 2 以降、DPI 125%/150%、GPU/大型モデル、Python 連携。

---

## 3. アーキテクチャ概要

```
[ユーザー操作] ─Ctrl+Shift+O?（予定）
      │
      ▼
[OCRClipboard.App]
  ├─ OverlayWindow (WPF) …… Display1/DPI100% 前提の矩形選択 UI
  ├─ WindowsMediaOcrEngine …… OCR 実行（約 100–300ms）
  ├─ PerfLogger ………………… [PERF]/[OCR] ログ出力
  └─ Clipboard ………………… クリップボード書き込み

補助ライブラリ：Ocr / Quality / Infra / Worker
ユニットテスト：tests/OCRClipboard.Tests（Fast テストのみ）
```

実装ファイルの配置例:

```
src/
 ├─ csharp/OCRClipboard.App/Program.cs        # エントリーポイント
 ├─ Ocr/WindowsMediaOcrEngine.cs              # OCR エンジン
 ├─ Quality/OcrQualityEvaluator.cs            # 品質ヒューリスティック
 └─ Infra/PerfLogger.cs                       # PERF/OCR ログ

tests/OCRClipboard.Tests/
 ├─ OcrResultTests.cs                         # CombinedText 等の確認
 ├─ OcrQualityEvaluatorTests.cs               # 品質ロジックのユニットテスト
 └─ WorkerTests.cs                            # JSON 入力の耐性テスト
```

---

## 4. 使い方

### 4.1 開発者向けショートカット

```pwsh
Remove-Item alias:gp -Force  # PowerShell 既定 gp (Get-ItemProperty) を削除
. .\scripts\ps_aliases.ps1   # gs / gp / check を読み込み

# 一括チェック: restore → build → dotnet format → dotnet test → typos
check
# Slow テストを含める: check -IncludeSlow
# フォーマットだけ確認: dotnet format "ver2.0_C#+Python_OCRClipboard.sln"
```

### 4.2 アプリ実行

```pwsh
# 通常実行（オーバーレイモード）
dotnet run --project src\csharp\OCRClipboard.App

# 画像ファイルテスト（実際のスクリーンショットでOCR性能検証）
dotnet run --project src\csharp\OCRClipboard.App -- --test-image test_images/sample.png
dotnet run --project src\csharp\OCRClipboard.App -- --test-image test_images/sample.png test_images/sample.txt
```

**📸 画像ファイルテストの詳細:**
- 実際のWebページや文書のスクリーンショットでOCR性能を検証
- 5回実行による統計分析（平均/最小/最大時間・精度）
- H0仮説検定（識字率 >= 95% かつ 処理時間 < 10秒）
- **すぐ試す:** [test_images/QUICK_START.md](test_images/QUICK_START.md)
- **完全ガイド:** [docs/IMAGE_TEST_GUIDE.md](docs/IMAGE_TEST_GUIDE.md)

実行時には `[タイミング分析]` と `[PERF]` 行で処理時間を、`[OCR]`/`[CLIPBOARD]` で認識結果を確認できます。ログ例は `src/csharp/OCRClipboard.App/logs/` に保存されます。

---

## 5. CI/CD

- **Build Validation** (`.github/workflows/build.yml`)
  - `dotnet restore`
  - `dotnet build --configuration Release --no-restore`
  - `dotnet format --verify-no-changes`
  - `dotnet test tests/OCRClipboard.Tests/OCRClipboard.Tests.csproj --filter "Category!=SlowOCR"`
  - `typos`（Chocolatey で自動導入）
- **Release** (`.github/workflows/release.yml`)
  - タグ `v*.*.*` で self-contained バイナリを生成し GitHub Releases に公開
- SlowOCR テストを自動化するには Windows 10+ の self-hosted runner が必要。詳細は `docs/CI_CD_STRATEGY.md` を参照。

---

## 6. 既知のギャップ

1. **常駐トレイ & ホットキー**（F-1/F-2/F-5）未実装。`NotifyIcon` + `RegisterHotKey` を組み込む。
2. **品質判定の配線**（F-6）。`OcrQualityEvaluator` を `Program.cs` へ接続し、CER/Accuracy と `[QUALITY]` ログを出力する。
3. **バイナリ・メモリ計測**（NF-3/NF-4）。`dotnet publish` とタスクマネージャで数値を取得し README / PROJECT_SPEC に追記する。
4. **Slow テスト実装**。`tests/Slow/WindowsMediaOcrIntegrationTests` を実装し、手動または self-hosted で検証する。

---

## 7. 参考情報

- `docs/TECHNICAL_LIMITS.md` … Windows.Media.Ocr の性能測定
- `docs/BENCHMARK.md` … 文字数と処理時間の相関
- `docs/DEBUG_MODE.md` … ログ出力を切り替えるデバッグフラグ
- `salvage/` … 旧 PaddleOCR 版のノウハウ（参考用、ビルド非対象）

過去の Python スクリプトを再利用する予定はありません。`start_ocr_worker.cmd` を実行してもワーカーは起動しない点に注意してください。

---

## 8. 変更履歴

- 2025-11-01: Windows.Media.Ocr 版ドキュメントへ刷新、`check` スクリプト導入、C# テストプロジェクト整備

開発に戻る際は、まず `check` で足元を整えたうえで要件ギャップ（常駐化・品質配線など）を埋めてください。
