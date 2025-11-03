# PowerShell コマンドチートシート

`scripts/ps_aliases.ps1` を PowerShell プロファイル（`$PROFILE`）でドットソースすると、日常作業に必要な 10 個のショートコマンドが利用できます。

```pwsh
# 例: プロファイルに以下を追記
. "$PSScriptRoot/../scripts/ps_aliases.ps1"
```

| エイリアス | 実行内容 | 用途 |
|-----------|----------|------|
| `tf` | `pytest -m "not slow" -q` | 速いテスト（実機 OCR なし） |
| `ts` | `pytest -m "slow" -q` | 実機 OCR を含む遅いテストだけ |
| `ta` | `pytest -q` | 総合テスト |
| `to` | `pytest tests/scripts/test_ocr_accuracy.py -q` | OCR 精度テスト専用 |
| `cw` | `python src/python/ocr_worker/main.py` | OCR ワーカー常駐起動 |
| `co` | `python ocr-screenshot-app/main.py --image ./test_image.png --no-clipboard` | サンプル画像で OCR 実行 |
| `lint` | `ruff check .` | 静的解析（lint） |
| `fmt` | `black 'ocr-screenshot-app' src/python` | コード整形 |
| `gs` | `git status -sb` | Git 作業ツリー状況を確認 |
| `gp` | `git push origin HEAD` | 現在ブランチを GitHub へ push |

> 補足  
> - すべて 10 文字以内のコマンドです。  
> - `co` はクリップボードへコピーしないよう `--no-clipboard` を付けています。必要ならオプションを外してください。  
> - `tf` / `ts` / `ta` は slow マーカーの運用ポリシーに合わせたモードです。
