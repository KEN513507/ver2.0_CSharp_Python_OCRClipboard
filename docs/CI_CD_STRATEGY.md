# CI/CD 戦略ドキュメント

## 現状の技術的制約

### Windows.Media.Ocr の制限
- **必要環境**: Windows 10 1809+ (Build 17763) クライアントOS
- **GitHub Actions標準**: Windows Server 2022（OCR API 非搭載）
- **結論**: 実機OCRテストはCI不可

### WPF Overlayの制限
- デスクトップGUI必須（Server Coreでは動作不可）
- Display 1専用、DPI 100%専用

---

## CI/CD 実装戦略

### Phase 1: ビルド検証のみ（✅ 実装済み）

**ワークフロー**: `.github/workflows/build.yml`

```yaml
トリガー: すべてのpush/PR
ランナー: windows-latest (Server 2022)
実行内容:
  - dotnet restore
  - dotnet build --configuration Release
  - 警告チェック
```

**制限事項**:
- ❌ テスト実行不可（テストプロジェクト.csproj未整備）
- ❌ OCR機能検証不可（API非対応OS）

---

### Phase 2: Fastテスト追加（今後実装）

**前提条件**:
1. テストプロジェクト.csproj作成
2. xUnit PackageReference追加
3. Fastテスト（モック使用）整備

**追加コマンド**:
```bash
dotnet test --filter "Category!=SlowOCR" --no-build
```

**除外されるテスト**:
- `[SlowOcr]` 属性付きテスト
- 実機OCR依存テスト

---

### Phase 3: リリース自動化（✅ 実装済み）

**ワークフロー**: `.github/workflows/release.yml`

```yaml
トリガー: vX.Y.Z タグpush
成果物:
  - OCRClipboard-vX.Y.Z-win-x64.zip (単一実行ファイル)
  - GitHub Release自動作成
```

**公開プロセス**:
```bash
# 1. タグ作成
git tag v1.0.0
git push origin v1.0.0

# 2. GitHub Actionsが自動実行
# 3. Releasesページに公開
```

---

## 実機テスト戦略

### Self-hosted Runner（将来的検討）

**必要環境**:
- Windows 10 Pro/Enterprise
- 日本語OCR言語パック（`Language.OCR~~~ja-JP~0.0.1.0`）
- DPI 100%固定モニター
- Display 1のみ接続

**設定手順**:
```bash
# Self-hosted runner登録
# Settings > Actions > Runners > New self-hosted runner
# Windows x64を選択して指示に従う

# ランナーマシンでの前提条件
Add-WindowsCapability -Online -Name Language.OCR~~~ja-JP~0.0.1.0
```

**ワークフロー修正**:
```yaml
jobs:
  integration-test:
    runs-on: self-hosted  # ← 専用ランナー使用
    steps:
      - run: dotnet test --filter "Category=SlowOCR"
```

---

### 現実的な運用（推奨）

**CI/CD**:
- ビルド検証のみ自動化
- Fastテストのみ自動化

**手動検証**:
```bash
# 開発マシンで実行
dotnet test --filter "Category=SlowOCR"

# 性能確認
dotnet run --project src/csharp/OCRClipboard.App
# → [PERF] ログで72-155msを確認
```

---

## 次のステップ

### 短期（今すぐ可能）
1. [x] ビルドCI作成（build.yml）
2. [x] リリースCI作成（release.yml）
3. [ ] 初回リリースタグ作成（v1.0.0）
4. [ ] リリース動作確認

### 中期（テストプロジェクト整備後）
1. [ ] tests/*.csproj作成
2. [ ] xUnit PackageReference追加
3. [ ] build.ymlにFastテスト追加

### 長期（必要に応じて）
1. [ ] Self-hosted Runner設置検討
2. [ ] 実機OCRテストのCI統合
3. [ ] パフォーマンス回帰テスト自動化

---

## トラブルシューティング

### ビルド失敗時
```bash
# ローカルで再現
dotnet build ver2.0_C#+Python_OCRClipboard.sln --configuration Release

# 警告確認
dotnet build 2>&1 | Select-String "warning"
```

### リリース失敗時
```bash
# 手動でpublish確認
dotnet publish src/csharp/OCRClipboard.App/OCRClipboard.App.csproj `
  -c Release -r win-x64 --self-contained `
  -p:PublishSingleFile=true

# 実行ファイルサイズ確認（目標: <20MB）
Get-Item .\bin\Release\net8.0-windows10.0.26100\win-x64\publish\OCRClipboard.App.exe
```

### OCRテスト失敗時（Self-hosted）
```bash
# 言語パック確認
Get-WindowsCapability -Online | Where-Object { $_.Name -like "*OCR*ja*" }

# DPI確認（100%必須）
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Screen]::PrimaryScreen.Bounds
```
