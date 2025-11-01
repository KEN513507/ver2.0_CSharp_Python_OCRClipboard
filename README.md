# OCR Clipboard v2.0 — Windows.Media.Ocr 版**現状の制限（2025-10-30）**

- Display 1 専用・DPI 100% 前提で品質保証

**本番実行: C# のみ / Python: 検証・解析用の工具箱**- 日本語 UI の OCR 最適化中（誤差は原文の25%または20文字まで、10秒以内を目標）

- 実機OCRは `pytest -m "slow"` で個別実行（通常テストから除外）

---- CLI出力は stdout の JSON、stderr は人間向けログ



## アーキテクチャ## 本番直前チェックリスト（2025-10-30）



### 本番バイナリ（C# 単独）- `pip list --outdated` で非互換アップデートに注意

- **範囲選択** → WPF オーバーレイ（Display 1 専用）- `pip freeze > requirements.txt` で依存ファイルを最新化

- **OCR エンジン** → `Windows.Media.Ocr`（日本語・英語、<1 秒）- `pipdeptree` で依存関係のねじれ・重複を確認

- **出力** → クリップボード直接コピー- `pytest` で最低限のユニット・統合テストを実行

- **常駐** → C# プロセスで完結（IPC なし）- `gh workflow run` でGitHub ActionsのCIが正常稼働するか確認

- `git log --oneline --graph` でマージ/リベース履歴の破綻がないか確認

### Python 工具箱（実行時非依存）- 本番環境で `docker-compose run` など仮想テストを行い、環境差異・DLL・DPI問題を排除

**場所**: `salvage/` ディレクトリに隔離  

**用途**: 研究・検証の最短路。本番実行パスには**一切かからない**。---

dotnet run --project src/csharp/OCRClipboard.App

| 用途 | 理由 |

|------|------|OCR Clipboard v2.0  IPC Skeleton

| **前処理・しきい値の検証** | C# より圧倒的に速く試作→数値で結論→C# 反映 |

| **評価ツール** | 文字誤差・Levenshtein・混同表・`[PERF]`/`[OCR]` ログ集計 |Overview

| **将来の診断用** | Windows.Media.Ocr 苦手パターンの切り分け（オフライン検証） |- C#コンソールアプリがPython OCRワーカーをJSON-over-stdio IPCで起動・連携。

| **テスト資産** | stdin 耐性・品質基準サンプル・モック雛形（C# とは別系統） |- DTOはC#・Pythonでミラー定義。



**いつでも削除可能**: Windows.Media.Ocr で十分なら `salvage/` ごと削除。設計負債ゼロ。【OCR判定ロジック追加】

OCR結果は「想定されるテキスト」と比較し、信頼度（confidence）閾値を用いて判定します。

---誤認・誤差判定は品質制約（原文の25%または最大20文字以内）と信頼度閾値の両方で管理します。

このロジックはOCR品質・要件定義にも適用されます。

## Quick Start（C# のみ）

- OCR結果・誤差はすべてログ出力し、品質管理。

```pwsh

# 1. リポジトリクローン【非要件定義（現状対応しない範囲）】

git clone https://github.com/KEN513507/ver2.0_CSharp_Python_OCRClipboard.git- ディスプレイ2（拡張画面）での正確な矩形選択・座標補正は未対応。

cd ver2.0_CSharp_Python_OCRClipboard- 仮想デスクトップ・複数ディスプレイの座標ズレ解消は今後の課題。

- GPU高速化・NamedPipe/gRPC IPCは将来対応予定。

# 2. C# アプリ起動（.NET 8 必須）

dotnet run --project src/csharp/OCRClipboard.App【現状の運用・注意点】

### テスト・コーディング運用方針

# 矩形選択 → OCR → クリップボード（1秒以内で完了）

```- **テストは仕様・閾値を明文化**：マージ判定や品質判定はテストでパラメータ（x_gap, y_overlap_ratio等）を明示し、期待値を固定。

- **外部依存（mss, tkinter）は使用元の名前空間にパッチ**：`@patch('ocr_sharp.capture.selector.mss')` など、import元ではなく使っている場所に刺す。

**Python は不要**。C# だけで完結します。- **OCRモデルはデフォルトでモック、遅い実機テストは @mark.slow で分離**：

   - `tests/conftest.py` の `_mock_paddleocr` により `ocr_screenshot_app.ocr.PaddleOCR` は軽量モック化（非 slow テストを高速化）。

---   - `tests/conftest.py` の `_mock_ocr_fast` により `tests/scripts/test_ocr_accuracy.py` のエンジン取得関数（`_get_yomitoku_ocr`/`_get_paddle_ocr`）を非 slow でフェイクに差し替え。`@pytest.mark.slow` が付いたテストでは実エンジンを使用。

   - 既定設定は `pyproject.toml` の `addopts = -q -m "not slow"`（slow はデフォルト除外）。

## Python 工具箱の使い方（任意）- **インポートパスは pyproject.toml でロック**：`pythonpath = [".", "src/python"]` でトップレベル・サブモジュール両方対応。

- **stdinループは空行・JSONエラーを握りつぶして継続**：`except json.JSONDecodeError: ... continue` で落ちない設計。

### 場所- **main.py の出力は人間向けは STDERR、機械向けは JSON**：`print(..., file=sys.stderr)` でデバッグ、人間向け。`print(json.dumps(...), flush=True)` で機械向け。

```- **品質閾値は環境変数で可変**：`OCR_MIN_CONFIDENCE` / `OCR_MAX_ABS_EDIT` / `OCR_MAX_REL_EDIT` を設定、CLI なら `--min-conf` 等で一時的に上書き可能。

salvage/- **テスト高速化・失敗時デバッグ**：`pytest -m "not slow" -q` で速いテストだけ。`pytest --maxfail=1 --lf` で失敗ケースだけ再実行。

├── tests/          # テスト雛形（品質しきい値・stdin 耐性）- プライマリディスプレイ（ディスプレイ1）でのみOCR品質を担保。

├── python/         # quality_config.py（しきい値計算ロジック）- 複数ディスプレイ環境では主画面のみ正確なOCR範囲選択が可能。

├── logs/           # performance_log_format.md（ログ書式）- 拡張画面でのズレ・誤認は現状仕様。今後改善予定。

├── capture/        # mss threading pattern

├── quality/        # heuristic validation### パフォーマンス・チューニング（即効版）

└── SALVAGE_INDEX.md  # 再利用資産インデックス

```#### 常駐ワーカーで初期化コストをゼロに



### いつ使うかデスクトップの `start_ocr_worker.cmd` をダブルクリックして常駐ワーカーを起動。

- **新しい前処理を試す時**: Python で数分実験→C# に反映ウォームアップ後、2回目以降は 2–3 秒台で応答します。

- **OCR 精度を数値化したい時**: Levenshtein・混同表で可視化

- **Windows.Media.Ocr が苦手なパターンに当たった時**: オフライン診断```pwsh

# 手動起動

### 使い方.\start_ocr_worker.cmd

```pwsh

# Python 環境セットアップ（初回のみ）# または PowerShell から直接

python -m venv .venv_analysis$env:PYTHONPATH=".;src\python;ocr-screenshot-app"

.\.venv_analysis\Scripts\Activate.ps1$env:OCR_PROFILE="mobile"

pip install python-Levenshtein pillowpython -m ocr_worker.main --mode resident

```

# 検証スクリプト実行

python salvage/python/quality_config.py  # しきい値計算例#### OCR モデルの選択

```

**OCR_PROFILE**: モデルの種類を指定（既定: `mobile`）

**注意**: `salvage/` は本番ビルドに含まれません。C# 実行パスに一切影響しません。- `mobile` — 高速・軽量（ppocrv3_mobile、推奨）

- `server` — 高精度・重量（PP-OCRv5_server、冷スタート90秒）

---

**モデルの配置**:

## Project Structure- **既定**: PaddleOCR が自動ダウンロード（`~/.paddlex/official_models/`）

- **手動配置**: `OCR_MODEL_ROOT` を設定して任意のディレクトリを指定

```  ```pwsh

src/  $env:OCR_MODEL_ROOT="D:\ocr_models"

├── csharp/  ```

│   ├── OCRClipboard.App/        # C# console app（Windows.Media.Ocr 統合）- **個別指定**: さらに細かく制御したい場合

│   │   ├── Program.cs           # メインエントリポイント  ```pwsh

│   │   └── Ocr/                 # （今後追加）WindowsOcrEngine.cs  $env:OCR_DET_DIR="D:\ocr_models\ppocrv3_mobile_det"

│   └── OCRClipboard.Overlay/    # WPF overlay（矩形選択）  $env:OCR_REC_DIR="D:\ocr_models\ppocrv3_mobile_rec"

│       └── OverlayWindow.xaml   # 選択 UI  ```

salvage/                         # Python 工具箱（実行時非依存）

└── SALVAGE_INDEX.md             # 再利用資産の説明#### CPU 最適化

```

```pwsh

---$env:OMP_NUM_THREADS="4"

$env:MKL_NUM_THREADS="4"

## Notes$env:FLAGS_use_mkldnn="true"

$env:FLAGS_fast_math="true"

- **Display 1 専用**: プライマリディスプレイのみ対応（マルチディスプレイ未対応）```

- **DPI 100% 推奨**: スケーリング設定は 100% で動作確認済み

- **キャプチャ画像**: デバッグ用に `logs/debug_capture.png` へ保存#### その他の環境変数



---- `OCR_CPU_THREADS` (default 4), `OCR_REC_BATCH_NUM` (default 8)

- `OCR_DET_LIMIT_SIDE_LEN` (default 960)

## Development- `OCR_LANG` (default "japan")



### C# ビルド・実行### 現状の性能ギャップと対策方針

```pwsh

# ビルド- **冷スタートが遅い**：`python ocr-screenshot-app/main.py --image ./test_image.png` を単発で実行すると、PaddleOCR のモデル展開と oneDNN 最適化が毎回走り 90〜100 秒かかる。UX 目標「範囲指定→10秒以内にOCR→クリップボード」は未達。

dotnet build- **常駐化が前提**：`src/python/ocr_worker/main.py` を常駐プロセスとして起動し、IPC（JSON-over-stdio）でリクエストを送る想定に切り替える。起動直後に小さな白画像でウォームアップさせれば、2回目以降は 2〜3 秒台まで短縮できる。

- **軽量モデルの明示**：`PP-OCRv5_server_*` は精度重視の大モデル。`OCR_DET_MODEL_DIR` / `OCR_REC_MODEL_DIR` をモバイル版に変更することで初期化コストと推論時間を抑えられる。

# 実行- **入力画像の軽量化**：キャプチャ後に長辺 1280px などへリサイズし、不要な UI 箇所を事前にトリミングする。CPU 負荷と推論時間を直接削減できる。

dotnet run --project src/csharp/OCRClipboard.App- **ハードの限界認識**：現行マシンは i7-8550U + Intel UHD 620（iGPU）のため GPU 加速は使えない。さらなる短縮が必要ならクラウド GPU もしくは新しい開発機（H/HS 系 CPU + RTX）の導入を検討。

```

### スクリーンキャプチャの安定化

### Python 工具箱（任意）- `mss` はスレッドローカルなハンドルを使うため、コンテキスト外／別スレッド使い回しはNG。

```pwsh- `ocr_screenshot_app/capture.py` の `grab_image` は「毎回 `with mss.mss()` で生成→その場で `grab()`→閉じる」方式に統一。グローバル保持しない。

# 仮想環境作成（初回のみ）- `mss` が失敗した場合は `PIL.ImageGrab` にフォールバック（stderrへ警告を出力）。

python -m venv .venv_analysis- Windows では `ocr-screenshot-app/main.py` 起動時に DPI awareness を向上（`SetProcessDpiAwareness(2)`、古い環境は `SetProcessDPIAware()` フォールバック）し、座標ズレを抑制。



# 有効化### 品質設定（QualityConfig）と上書き順序

.\.venv_analysis\Scripts\Activate.ps1- 既定値: confidence ≥ 0.70, Levenshtein ≤ min(25% of ref, 20 chars)

- 上書き優先度: DTO > 環境変数 > 既定値

# 必要なパッケージインストール   - 現時点では DTO からの上書きは未提供（将来追加予定）。環境変数の上書きは有効です。

pip install python-Levenshtein pillow- 環境変数での上書き:

```   - OCR_MIN_CONFIDENCE, OCR_MAX_REL_EDIT, OCR_MAX_ABS_EDIT, OCR_BASE_ERROR_FLOOR

   - OCR_MIN_CONF_LENGTH, OCR_MIN_ALPHA_RATIO, OCR_MIN_LENGTH_RATIO

---   - OCR_NORMALIZE_NFKC (true/false), OCR_IGNORE_CASE (true/false)

- 判定時の正規化:

## Archive Info   - NFKC 正規化と大文字小文字無視（既定で有効）を適用後に閾値判定を行います。



- **ブランチ**: `archive/paddle-to-wm-ocr`Quick Start

- **タグ**: `v2-archive`1) Python（`python`）と.NET SDKをインストール。

- **理由**: PaddleOCR は性能要件（2-3 秒）を満たせず（実測 82 秒）2) repo rootからC#アプリを起動（Pythonワーカー・オーバーレイも自動起動）:

   - `dotnet run --project src/csharp/OCRClipboard.App`

詳細は `salvage/SALVAGE_INDEX.md` を参照。

# ⚠️ プロジェクト終了通知（2025-11-01）

---

**本プロジェクトは終了しました。今後は Windows.Media.Ocr 単独構成を推奨します。**

## License

---

MIT License

## 終了理由

### 性能要件との不一致
- **目標**: 2回目以降のOCRを 2-3 秒以内で完了
- **実測**: PaddleOCR（server モデル）で平均 82 秒、mobile モデルは API 不明で未検証
- **ハードウェア制約**: i7-8550U（モバイル U 系 CPU）+ Intel UHD 620（iGPU のみ）では大型モデルの高速化は不可能

### 技術選定の誤り
- **PaddleOCR**: 初回 90 秒、常駐化後も 80 秒超（40倍遅い）
- **Windows Snipping Tool**: GPU なしで <1 秒の高速 OCR を実現
- **結論**: Windows.Media.Ocr API が本要件に最適（OS 統合、軽量、高速）

---

## 再利用可能な資産（サルベージ済み）

`salvage/` ディレクトリに以下の設計パターン・知見を保管:

| 分野 | 内容 | 適用価値 |
|------|------|---------|
| **キャプチャ** | mss スレッドセーフパターン + PIL フォールバック + DPI awareness | WPF/WinUI3 マルチスレッド対応 |
| **テスト** | pytest slow マーク分離 + autouse モック | CI 実行時間 90% 削減 |
| **品質判定** | Levenshtein + 記号比率 + 長さ比ヒューリスティック | スコアレス OCR の品質保証 |
| **計測** | `[PERF]` / `[OCR]` ログ書式 | ボトルネック特定・リグレッション検出 |

詳細は **`salvage/SALVAGE_INDEX.md`** を参照。

---

## 次回の推奨構成

**C# 単独 + Windows.Media.Ocr（100 行以内で完結）**:

```csharp
// 1. WPF で矩形選択
// 2. Windows.Graphics.Capture で画面キャプチャ
// 3. Windows.Media.Ocr.OcrEngine で日本語 OCR（<1 秒）
// 4. クリップボードにコピー

using Windows.Media.Ocr;
var engine = OcrEngine.TryCreateFromLanguage(new Language("ja"));
var result = await engine.RecognizeAsync(bitmap);
Clipboard.SetText(result.Text);  // <1 秒で完了
```

**PaddleOCR は不要。軽い・速い・OS 統合済み。**

---

## アーカイブ情報

- **ブランチ**: `archive/paddle-to-wm-ocr`
- **タグ**: `v2-archive` — "Archived: pivot to Windows.Media.Ocr single-model plan"
- **削除済み**: Python 環境、PaddleOCR 依存、IPC レイヤー、pytest インフラ
- **保管済み**: 再利用価値ある設計パターン（`salvage/`）

---

# （以下は旧 README — 参考用）

## OCR Clipboard v2.0 - IPC Skeleton（終了版）

Project Structure
- `src/csharp/OCRClipboard.App` — C# console app, DTOs, and IPC client（削除予定）
- `src/csharp/OCRClipboard.Overlay` — WPF overlay (single monitor), selection → PNG capture
- ~~`src/python/ocr_worker`~~ — Python worker（削除済み）

Notes
- ~~C#ホストは`PYTHONPATH`を`src/python`に設定~~ — 削除済み
- ~~Pythonワーカーは`-u`（アンバッファ）で即時出力~~ — 削除済み
- オーバーレイ・選択は常に主画面の物理ピクセル座標で動作

### 30秒スモークチェック
```bash
python ocr-screenshot-app/main.py --image ./test_image.png | python -c "import sys,json; data=json.load(sys.stdin); assert 'texts' in data and data['texts']"
pytest -m "not slow" --maxfail=1
```

slow を含めて実機で確認する場合:

```bash
pytest -m "slow" -q
```

---
## 現状の課題・注意点

- ディスプレイ1（主画面）では矩形選択範囲が正確にOCR可能。
- ディスプレイ2（拡張画面）では選択範囲が大きくズレる現象あり。
- 原因は座標系・DPI・仮想スクリーンの扱い。
- 今後、複数ディスプレイでも正確な範囲指定ができるよう修正予定。
- この注意書きは課題解決後に削除してください。

## OCR機能について

- **現状はプライマリ画面のみ対応、セカンダリ画面は今後検討予定。**
- OCR精度向上のため、画像前処理（リサイズ・ノイズ除去・適応的閾値処理・エッジ強調）と品質判定（文字誤差は原文の25%以内かつ最大20文字、信頼度0.7以上）を導入。
- 品質判定に不合格の場合、ログに誤差情報を出力（置換・削除・挿入パターンを詳細分析）。
- OCRエンジンとしてyomitokuを使用（10秒タイムアウト、PaddleOCRフォールバック）。
- テストパターン・実画像でのOCR精度検証は100%/125%/150%スケールで実施。

## 本番直前チェックリスト

- pip list --outdated を確認し、非互換アップデートに注意
- pip freeze > requirements.txt を最新化したか？
- pipdeptree で依存のねじれを確認したか？
- pytest で最低限のユニット・統合テストを実行したか？
- gh workflow run で GitHub Actions が生きてるか試したか？
- git log --oneline --graph でマージ/リベースに破綻がないか？
- 本番環境で docker-compose run など仮想テストを行ったか？

---
## エイリアス登録・コマンドチートシート

### PowerShell エイリアススクリプト

`scripts/ps_aliases.ps1` を新規作成し、以下 10 コマンドを関数として定義しています。  
（`tf`, `ts`, `ta`, `to`, `cw`, `co`, `lint`, `fmt`, `gs`, `gp`）

- `$PROFILE` などから `.`（ドットソース）で一括読み込み可能です。
- 例: `.` `$HOME\Documents\Projects\ver2_0_CSharp_Python_OCRClipboard\scripts\ps_aliases.ps1`

### コマンドチートシート

`docs/command_cheatsheet.md` を追加。  
上記 10 コマンドの用途・実行例・読み込み方法を表形式でまとめています。

| コマンド | 用途                       | 実行例・備考                |
|----------|----------------------------|-----------------------------|
| tf       | テスト全実行               | `tf` → `pytest`             |
| ts       | テスト高速化（slow除外）   | `ts` → `pytest -m "not slow"` |
| ta       | テスト全件（slow含む）     | `ta` → `pytest -m "slow or not slow"` |
| to       | テスト失敗のみ再実行       | `to` → `pytest --maxfail=1 --lf` |
| cw       | C#ビルド                   | `cw` → `dotnet build`       |
| co       | C#実行                     | `co` → `dotnet run --project src/csharp/OCRClipboard.App` |
| lint     | Pythonコード検査           | `lint` → `flake8 src/python`|
| fmt      | Python自動整形             | `fmt` → `black src/python`  |
| gs       | Gitステータス表示          | `gs` → `git status`         |
| gp       | Gitコミット＆プッシュ       | `gp` → `git commit -am "..." ; git push` |

詳細は `docs/command_cheatsheet.md` を参照してください。