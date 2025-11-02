# OCR Clipboard v2.0 開発仕様

> **備考**: このファイルは UX とプロセス分解の概要をまとめたものです。最新の要件定義・DFD/ER 図・実装状況は `docs/requirements_trace_20251102.md` を必ず参照してください。推奨読順は「1. `docs/requirements_trace_20251102.md` → 2. `PROJECT_SPEC.md`（本書）→ 3. `docs/DOCUMENTATION_NAV.md`」です。

## 概要
- C#（WinUI3）＋Pythonの二層構成
- 10秒以内・誤差≤4文字の品質制約
- テスト画像セット（A1〜E1）・期待語句は test_cases.json に準拠

---

## DFD（Data Flow Diagram）

### レベル0（コンテキスト図）

```
┌────────────┐           ┌──────────────┐
│    ユーザー   │──操作──▶│  Capture/OCR  │──テキスト→クリップボード/保存
└────────────┘           └──────────────┘
         ▲                         │
         └────ログ/結果の確認───────┘
```

- システム境界内に C# フロントエンド（WinUI3）と Python OCR バックエンド。
- 出力はクリップボード貼り付け or ファイル保存、ログ記録。

### レベル1（モジュール分解）

```
[外部] ユーザー
   │ Hotkey
   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│             C# Frontend (WinUI3) & Native Capture                         │
│                                                                            │
│ P1 ホットキー監視 ──▶ P2 モニタ特定 ──▶ P3 オーバーレイ&矩形選択             │
│     │設定読込(D1)         │(GetCursorPos/MonitorFromPoint)                 │
│     ▼                     ▼                                                │
│ P4 モニタキャプチャ(Windows.Graphics.Capture) ─▶ P5 前処理/切抜              │
│                                          │                                 │
│                                          ├─▶ D3 画像キャッシュ               │
│                                          ▼                                 │
│                             P6 OCRディスパッチ(IPC: NamedPipe/gRPC)        │
│                                          │                                 │
│                                          ▼                                 │
│                             Python Backend (yomitoku 等)                    │
│                             P7 推論 → P8 後処理(正規化/半全角/句読点)         │
│                                          │                                 │
│                                          ├─▶ D4 結果ログ/品質 (JSON/CSV)     │
│                                          └─▶ P9 出力(Clipboard/保存)         │
└────────────────────────────────────────────────────────────────────────────┘
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

## 実装メモ（矩形選択 → OCR 実行パイプライン）

- 矩形ドラッグの描画とバウンディングボックスの組み立ては `src/csharp/OCRClipboard.Overlay/OverlayWindow.xaml.cs` の `OnMouseDown`（近傍 76 行）、`UpdateSelectionRect`（近傍 100 行）、`ConfirmSelectionAndClose`（近傍 111 行）で実装。WPF の DIP 座標からモニタ物理ピクセルへ変換して `SelectionResult` を生成する。
- 切り出した関心領域を PNG → Base64 に変換して返すスレッド処理は `src/csharp/OCRClipboard.Overlay/OverlayRunner.cs:9` 付近。
- 取得した Base64 を受け取り、`CaptureService.CaptureToPng(...)` でキャプチャし OCR リクエストに載せるのは `src/csharp/OCRClipboard.App/Program.cs:47` 付近。
- OCR ディスパッチでは PaddleOCR の `dt_boxes` 判定を `len(dt_boxes) == 0` で実施し、NumPy 配列に対する `if not dt_boxes:` 判定は避ける（truth value ambiguous 例外対策）。


結論：**だいたい合ってる**。ただし “本番” 観点で **数点だけ明文化／差し替え**すると、今回の学び（罫線無視・高密度/低コントラスト対策・ハイパラ可変）まで仕様にきれいに落ちます。

---

# 仕様の差し替え／追記ポイント（即時反映推奨）

## 0) 品質目標の二段建て（試験と本番を整合）

* **本番SLA**：**応答 ≤ 10s** かつ **誤差 ≤ 4文字**（Levenshtein）
* **評価SLA**（データセット）：“文字種・密度別の適応阈値”で判定
  * 既定：**CER ≤ 0.30**
  * `dense`：**CER ≤ 0.30**（将来0.25を目標）
  * `mono-code`：**CER ≤ 0.35**（空白保持・罫線無視を前提）
  * `lowcontrast-dense`：**CER ≤ 0.35**（将来0.30を目標）
> 運用上は「本番＝≤4文字」「回帰試験＝CER適応」の二系統を並走させる、と明記。

## 1) 正規化と罫線無視（評価にも本番にも入れる）

* `normalize_for_eval(text, keep_spaces=False, ignore_boxdrawing=True)` を handler.py の共通関数として実装。
  * `mono-code`タグ時は `keep_spaces=True`（空白保持）
  * 全モードで `ignore_boxdrawing=True`（罫線は無視）
* ロギング：正規化前後の 50 文字プレビューを JSON に出力（`before/after`）。
## 2) OCRエンジンのハイパラを環境変数で完全制御

PaddleOCR 初期化（handler.py）に以下を反映し、ログで実値を必ず出力：
OCR_DET_DB_THRESH (float, default 0.25)
OCR_DET_DB_BOX_THRESH (float, default 0.55)
OCR_DET_DB_UNCLIP (float, default 2.0)
OCR_DET_LIMIT_SIDE_LEN (int, default 1536/1920)
OCR_REC_BATCH_NUM (int, default 1)
OCR_DROP_SCORE (float, default 0.5)
OCR_PADDLE_USE_DILATION (bool, default false)
OCR_PADDLE_BINARIZE (bool, default false)
OCR_PADDLE_INVERT (bool, default false)
* キャッシュキーにこれらを含め、設定差で別インスタンスを持てるように。

## 3) フォールバック方針（本番の決め）

* 既定は PaddleOCR を第一選択。
* yomitoku フォールバック条件（本番のみ）：`dt_boxes < 3`、暫定CERが閾値+0.3超、出力長が期待長の10%未満（推定）のいずれか。
* 評価中は `YOMITOKU_DISABLE=1` で固定（再現性確保）。

## 4) タグ駆動の前処理＆言語プリセット

* `mono-code`：行単位で JP / EN を再認識し、`score = 0.6·CTC不確実度 + 0.3·記号不一致 + 0.1·かな混入ペナルティ` を比較して小さい方を採用。空白保持、罫線無視、記号補正。
* `dense`：`det_limit_side_len=1920`、`det_db_thresh≈0.18–0.20`、`det_db_box≈0.45–0.50`、`unclip≈1.8–2.0`。
* `lowcontrast(-dense)`：`use_dilation=1`、`binarize=1`、必要時 `invert=1`、CLAHE(clipLimit=4.0, grid 6x6)。
* 共通前処理：水平・垂直方向の極細線（罫線）をモルフォロジー（`cv.morphologyEx` の `MORPH_OPEN` / `MORPH_CLOSE` 併用）でマスク → 白塗りし、OCR 前に除去。

## 5) IPCは Named Pipe に一本化（本番設計）

* ローカル単機能アプリのため NamedPipe 推奨（gRPC は将来オプション）。
* プロトコル：`{req_id, image(meta or shm handle), lang_hint, tags, timeout_ms}` → `{req_id, text, confidence, boxes?, timings, quality_gate}`。
* タイムアウトは既定 8s（UI〜出力合計で10s SLAを満たす余地）。

## 6) 時間配分（SLA を守るための運用）

* 初回起動時にウォームアップ（`ensure_warmup_languages`、JP/EN）。
* 失敗時は `det_limit_side_len` を 1920→1536→1280 と段階的に下げ再試行（各1回、全体10s以内）。

## 7) ログと計測（再現性のために必須）

* `proc_total / capture_ms / ocr_ms / post_ms` を各リクエストで計測し JSON に保存（D4）。
* Paddle の `dt_boxes` 件数と実ハイパラ値を毎回記録。
* “品質門番” の判定根拠（`rule=levenshtein<=4` or `rule=cer<=thr`）を明示。

## 8) テスト項目の明文化（A1〜E1 + 回帰）

* 機能：ホットキー→矩形→結果がクリップボード、10s 内。
* 品質：各タグ別ケースが上記評価 SLA を満たす。
* 退行：罫線無視をオンにしても罫線なし画像の CER に劣化がない。
* 耐障害：`dt_boxes=0` や超時はフォールバック / デグレードで “何も返さない” を避ける。

# DFDへの最小修正（差分だけ）

* P6 OCRディスパッチ：NamedPipe を標準とし、gRPC は脚注扱い。
* P7 推論：Paddle→条件付き yomitoku の順を明記。
* P8 後処理：`normalize_for_eval(keep_spaces=mono-code)` と罫線無視を明記。
* D1 設定/プリセット：タグ別プロファイル（dense / lowcontrast / mono-code）を格納。

# すぐ試す実行プリセット（本番向け）

高密度＋低コントラストに強める例：
```
$env:YOMITOKU_DISABLE        = "0"
$env:OCR_DET_DB_THRESH       = "0.20"
$env:OCR_DET_DB_BOX_THRESH   = "0.50"
$env:OCR_DET_DB_UNCLIP       = "1.8"
$env:OCR_DET_LIMIT_SIDE_LEN  = "1920"
$env:OCR_REC_BATCH_NUM       = "1"
$env:OCR_PADDLE_USE_DILATION = "1"
$env:OCR_PADDLE_BINARIZE     = "1"
$env:OCR_PADDLE_INVERT       = "0"
```

## まとめ

* 本仕様全体の方向性は妥当。
* 上記 8 点を追記することで、罫線無視・タグ別対処・ハイパラ可変・フォールバック条件が本番仕様に反映される。
* これで 008 は CER 0.3 台前半、002/012 は 0.3 目標への到達を狙える。
