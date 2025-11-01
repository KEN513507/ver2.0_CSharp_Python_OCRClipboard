# CI/CD Strategy (Windows.Media.Ocr)

## 1. Scope

- 対象は C#/.NET 8 の Windows.Media.Ocr 構成のみ。
- Python / PaddleOCR は削除済み。`start_ocr_worker.cmd` などは触らない。
- SlowOCR（実機）テストは手動または self-hosted runner で運用する。

---

## 2. 現在のワークフロー

### Build Validation (`.github/workflows/build.yml`)

| 順序 | 内容 |
|------|------|
| 1 | checkout + setup-dotnet (8.0.x) |
| 2 | `dotnet restore ver2.0_C#+Python_OCRClipboard.sln` |
| 3 | `dotnet build … --configuration Release --no-restore` |
| 4 | `dotnet format … --verify-no-changes --severity error --no-restore` |
| 5 | `dotnet test tests/OCRClipboard.Tests/OCRClipboard.Tests.csproj --configuration Release --filter "Category!=SlowOCR"` |
| 6 | `choco install typos -y` |
| 7 | `typos` |

つまり **ビルド / フォーマット / Fast テスト / typos** を CI で強制している。SlowOCR テストは trait filter により除外される。

### Release (`.github/workflows/release.yml`)

- トリガー: `v*.*.*` タグ push
- 実行: `dotnet publish` で self-contained バイナリを生成し、ZIP を GitHub Releases に添付
- 依存: .NET 8 ランタイムのみ（Python 依存なし）

---

## 3. SlowOCR 自動化（任意）

1. Windows 10/11 の self-hosted runner を登録
2. 日本語 OCR 言語パックをインストール
   ```powershell
   Add-WindowsCapability -Online -Name Language.OCR~~~ja-JP~0.0.1.0
   ```
3. Display 1 / DPI 100% を維持
4. Slow テスト専用ジョブ例:
   ```yaml
   jobs:
     slow-test:
       runs-on: self-hosted
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-dotnet@v4
           with:
             dotnet-version: '8.0.x'
         - run: dotnet test tests/OCRClipboard.Tests/OCRClipboard.Tests.csproj --configuration Release --filter "Category=SlowOCR"
   ```

---

## 4. ローカル運用

| 目的 | コマンド | 備考 |
|------|----------|------|
| CI と同じ検証 | `check` | `scripts/run_dev_checks.ps1`（restore → build → format → test → typos） |
| Slow テスト | `dotnet test --filter "Category=SlowOCR"` | 実機でのみ実行可能 |
| パフォーマンス確認 | `dotnet run --project src\csharp\OCRClipboard.App` | `[PERF]` ログを参照 |

---

## 5. Troubleshooting

- **dotnet format 失敗**: ローカルで `dotnet format` を実行し差分をコミット。
- **typos 未導入**: `choco install typos -y`。一時的に省きたい場合は `check -SkipTypos`。
- **Slow テストが動かない**: Windows Server では OCR API が無効。必ず Windows 10/11 クライアントで実行する。

---

## 6. 今後の課題

- self-hosted runner を導入して SlowOCR テストを自動化
- バイナリサイズ／メモリ使用量を CI で可視化（NF-3/NF-4 の証跡）
- `check` と CI の結果を監査ログとして保管する仕組みの整備
