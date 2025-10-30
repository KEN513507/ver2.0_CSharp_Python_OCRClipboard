# ocr_sharp - DPI完全対応・高精度・自動クリップボードOCRアプリ

## ディレクトリ構成
```
ocr_sharp/
├── capture/
│   └── selector.py          # 矩形選択 + キャプチャ
├── ocr/
│   └── recognizer.py        # PaddleOCR実行部分
├── main.py                  # エントリポイント
├── fonts/
│   └── NotoSansCJKjp.otf    # フォント（OCR描画用）
├── images/
│   └── last_capture.png     # 直前のキャプチャ画像
├── requirements.txt
└── README.md
```

## 特徴
- DPI Awareness完全対応（Windowsで座標ズレなし）
- PaddleOCR日本語モデルで高精度認識
- Tkinterで矩形選択、mssで1px単位キャプチャ
- クリップボード自動コピー
- Display 1専用（DPI 100%推奨）

## インストール
```pwsh
pip install -r requirements.txt
```

## 実行方法
```pwsh
python main.py
```

## 注意
- DPIスケーリングは100%で実行してください
- デュアルモニタ環境では必ずDisplay 1でキャプチャしてください
- draw_ocr利用時はfonts/NotoSansCJKjp.otfが必要

## ライセンス
MIT
