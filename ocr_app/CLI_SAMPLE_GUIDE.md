# PaddleOCR CLI Sample (`ocr_app`)

このディレクトリは PaddleOCR を手軽に試すための **練習用コマンド（CLI）集** です。実際のアプリ開発は別ディレクトリ（`ocr_sharp` や C# アプリ）で行い、ここでは「文字がどのくらい読めるか」「表示倍率（DPI）が変わるとどうなるか」を気軽に試します。

## ディレクトリ構成

```
ocr_app/
├── main.py               # 実行ファイル
├── requirements.txt      # pip install -r requirements.txt
├── images/
│   └── input.jpg         # 検証用画像
├── fonts/
│   └── NotoSansCJKjp-Regular.otf # draw_ocr用フォント
└── CLI_SAMPLE_GUIDE.md
```

## 実行方法

1. 必要なパッケージをインストール
   ```pwsh
   pip install -r requirements.txt
   ```
2. 画像を images/input.jpg に配置
3. main.py を実行
   ```pwsh
   python main.py
   ```

## DPI・座標ズレ対策
- Windows では表示倍率（DPI）が 100% であることが前提です。  
  125% 以上にすると座標がずれて読み取りに失敗します。
- OCR は Display 1（メイン画面）で実行してください。サブモニタでは座標がずれます。
- `main.py` 内のコメントを参考に、縮小・拡大やノイズ除去の設定を調整できます。

## 注意事項
- `draw_ocr()` で結果を画像に描く場合は `fonts/NotoSansCJKjp-Regular.otf` を配置してください。
- 実際にアプリとして使いたい場合は `ocr_sharp/OPERATIONS_GUIDE.md` を参照してください。
- プロジェクト全体の位置づけや他ディレクトリとの違いはルート `README.md` にまとめています。
