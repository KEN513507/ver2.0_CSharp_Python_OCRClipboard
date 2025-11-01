[PERF] ログと OCR 結果ログのフォーマット例
==========================================

```
[PERF] capture=42.5ms preproc=7.4ms infer=87112.8ms postproc=0.2ms total=87166.6ms
[OCR] n_fragments=16 mean_conf=0.97 min_conf=0.77
```

使いどころ
----------

- `capture`  … `capture.grab_image` で矩形キャプチャに掛かった時間。
- `preproc`  … 画像のリサイズや正規化。
- `infer`    … OCR inference に掛かった時間。
- `postproc` … テキストマージやクリーニング。
- `total`    … 一連の処理時間。
- `n_fragments` / `mean_conf` / `min_conf` … OCR ヒューリスティック評価の基礎指標。

運用ヒント
----------

1. `time.perf_counter()` で区間計測する。  
2. ログは `stderr` に出力し、`stdout` は JSON 応答のみ。  
3. CI や実機検証で差分比較するときもフォーマットを統一できる。  
4. もし複数リクエストを束ねるなら `infer` の平均値を sliding window で管理する。
