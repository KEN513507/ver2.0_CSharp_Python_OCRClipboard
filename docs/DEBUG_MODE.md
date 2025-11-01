# デバッグモード切り替えガイド

## 概要
大量の座標計算ログ（[COORD], [SELECT], [C#] OcrResult angle等）がサマリーを埋もれさせる問題を解決するため、**デバッグモードのON/OFF機能**を実装しました。

---

## 使い方

### 🔇 通常モード（デフォルト）
**ユーザーが見たい情報だけを表示**

```pwsh
dotnet run --project src\csharp\OCRClipboard.App\OCRClipboard.App.csproj
```

**表示される内容**:
- ✅ `[タイミング分析]` ブロック（proc_total, user, grab, pre, ocr, post）
- ✅ `[テキスト全文]`
- ✅ `[クリップボード]` 状態
- ✅ `[PERF]` 機械処理用ログ（CI/CD連携用）
- ✅ `[OCR]` サマリー（fragments数、信頼度）

**表示されない内容**（ノイズ削減）:
- ❌ `[C#] Starting Windows.Media.Ocr engine...`
- ❌ `[C#] Done.`
- ❌ `[OCR] Engine=Windows.Media.Ocr lang='ja'`
- ❌ `[COORD]` 座標計算詳細（15行）
- ❌ `[SELECT]` 選択範囲詳細（10行）
- ❌ `[C#] OcrResult angle=-0.00°`
- ❌ デバッグキャプチャ保存メッセージ

---

### 🔊 デバッグモード
**開発者向け詳細ログ**

```pwsh
$env:OCR_DEBUG="1"
dotnet run --project src\csharp\OCRClipboard.App\OCRClipboard.App.csproj
```

**追加で表示される内容**:
- ✅ `[C#] Starting/Done` メッセージ
- ✅ `[OCR] Engine=...` 言語初期化ログ
- ✅ `[COORD]` 全座標詳細（DPIスケール、モニター座標等）
- ✅ `[SELECT]` 選択範囲変換詳細（物理座標vs期待値）
- ✅ `[C#] OcrResult angle=...` テキスト傾き
- ✅ `[C#] Debug capture saved: ...`

---

## 実装詳細

### 環境変数チェック
各ファイルで以下のように実装：

```csharp
// デバッグモード制御（環境変数 OCR_DEBUG=1 で有効化）
private static readonly bool DebugMode = Environment.GetEnvironmentVariable("OCR_DEBUG") == "1";
```

### 対象ファイル
1. **Program.cs** (OCRClipboard.App)
   - `[C#] Starting/Done` メッセージ
   - デバッグキャプチャ保存ログ

2. **WindowsMediaOcrEngine.cs** (Ocr)
   - `[OCR] Engine=...` 言語初期化
   - `[C#] OcrResult angle=...` テキスト傾き

3. **OverlayWindow.xaml.cs** (OCRClipboard.Overlay)
   - `LogMonitorAndWindowState()` - 15行の [COORD] ログ
   - `LogSelection()` - 10行の [SELECT] ログ

---

## 効果

### Before（デバッグモードOFF前）
```
[C#] Starting Windows.Media.Ocr engine...
[OCR] Engine=Windows.Media.Ocr lang='ja'
[COORD] === Monitor & Window Coordinates ===
[COORD] rcMonitor (physical px): Left=0, Top=0, Right=1920, Bottom=1080
[COORD] Monitor size (physical): 1920 x 1080
[COORD] DPI Scale: X=1.0000, Y=1.0000
... （全15行）
[SELECT] === User Selection ===
[SELECT] Logical rect (DIPs): X=100.00, Y=50.00, W=800.00, H=40.00
... （全10行）
[C#] OcrResult angle=-0.00°
[C#] OcrResult angle=-0.00°
[C#] OcrResult angle=-0.00°
================================================
[タイミング分析] proc_total=250ms (SLA目標: <400ms)
  ├─ user      : 2500ms  (人間の選択時間 - 評価対象外)
  ├─ grab      : 10ms  (画像取得)
  ├─ pre       : 5ms  (前処理)
  ├─ ocr       : 230ms  (OCR推論) ★重要
  ├─ post      : 5ms  (後処理)
  └─ wall_total: 2750ms (全体 - 参考値)
[OCR結果] fragments=50, confidence=0.98
[テキスト全文]
これはOCRテストです。
[クリップボード] コピー=True, 文字数=15
================================================
[C#] Done.
```

**問題**: サマリー（[タイミング分析]）がノイズに埋もれて見つけにくい

---

### After（デバッグモードOFF後）
```
================================================
[タイミング分析] proc_total=250ms (SLA目標: <400ms)
  ├─ user      : 2500ms  (人間の選択時間 - 評価対象外)
  ├─ grab      : 10ms  (画像取得)
  ├─ pre       : 5ms  (前処理)
  ├─ ocr       : 230ms  (OCR推論) ★重要
  ├─ post      : 5ms  (後処理)
  └─ wall_total: 2750ms (全体 - 参考値)
[OCR結果] fragments=50, confidence=0.98
[テキスト全文]
これはOCRテストです。
[クリップボード] コピー=True, 文字数=15
================================================
[PERF] user=2500ms grab=10ms pre=5ms ocr=230ms post=5ms proc_total=250ms wall_total=2750ms
[OCR] n_fragments=50 mean_conf=0.98 sample="これはOCRテストです。"
```

**改善**: 
- ✅ サマリーが最初に表示される（ノイズゼロ）
- ✅ 読み飛ばす必要がない
- ✅ 重要な情報（proc_total, OCR結果）が一目で分かる
- ✅ `[PERF]` ラインは機械処理用に残す（CI/CD連携）

---

## まとめ

| モード | 用途 | 表示量 | 対象ユーザー |
|--------|------|--------|------------|
| **通常**（デフォルト） | 日常利用 | 最小限（サマリーのみ） | エンドユーザー |
| **デバッグ**（OCR_DEBUG=1） | 問題調査 | 全詳細ログ | 開発者 |

**推奨運用**:
- 本番リリース時は**デバッグモードOFF**がデフォルト
- トラブルシューティング時のみ `$env:OCR_DEBUG="1"` で有効化
