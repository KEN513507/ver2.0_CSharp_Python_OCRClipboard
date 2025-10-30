# PaddleOCR 実用サンプル

## ディレクトリ構成

```
ocr_app/
├── main.py               # 実行ファイル
├── requirements.txt      # pip install -r requirements.txt
├── images/
│   └── input.jpg         # 検証用画像
├── fonts/
│   └── NotoSansCJKjp-Regular.otf # draw_ocr用フォント
└── README.md
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
- Windows環境ではDPIスケーリングを100%に固定推奨
- キャプチャ・OCRは常にディスプレイ1（メイン画面）で実行
- 方向補正・解像度調整は main.py 内で設定可能

## 注意事項
- draw_ocr()を使う場合は fonts/NotoSansCJKjp-Regular.otf が必要
- デュアルモニタ環境では、必ずメイン画面でキャプチャしてください
