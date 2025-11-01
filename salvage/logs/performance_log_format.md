# [PERF] / [OCR] ログフォーマット

```
[PERF] capture=42.5ms preproc=7.4ms infer=87112.8ms postproc=0.2ms total=87166.6ms
[OCR] n_fragments=16 mean_conf=0.97 min_conf=0.77
```

- capture: Rect 選択 → Bitmap 取得
- preproc: 前処理（リサイズ・正規化）
- infer: OCR 推論 (Windows.Media.Ocr)
- postproc: テキスト整形や品質判定
- total: 全体時間
- n_fragments / mean_conf / min_conf: 品質チェックに使う基礎値

C# 実装: `src/Infra/PerfLogger.cs`
