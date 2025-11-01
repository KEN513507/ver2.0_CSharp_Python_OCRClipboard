# PowerShell Helper Commands

プロジェクト直下で次を実行するとエイリアスが読み込まれ、定型作業を素早く実行できます。

```pwsh
# PowerShell 既定の gp エイリアス (Get-ItemProperty) と衝突するため、先に削除
Remove-Item alias:gp -Force

# エイリアスを読み込み
. .\scripts\ps_aliases.ps1
```

| コマンド | 実行内容 | 用途 |
|----------|----------|------|
| `gs` | `git status -sb` | 作業ツリーの差分確認 |
| `gp` | `git push origin HEAD` | 現在のブランチをリモートへ push |
| `check` | `scripts/run_dev_checks.ps1` | Restore → Build → `dotnet format` → テスト → `typos` を一括実行 |

`check` には以下のオプションがあります。

- `-IncludeSlow` … `Category=SlowOCR` の遅いテストも実行
- `-SkipBuild` … `dotnet restore` / `dotnet build` を省略（事前にビルドが済んでいる場合）
- `-SkipFormat` … `dotnet format --verify-no-changes` を省略
- `-SkipTypos` … スペルチェック (`typos`) を省略

> `typos` CLI が未導入の場合は `cargo install typos-cli` もしくは `choco install typos` を実行してください。
