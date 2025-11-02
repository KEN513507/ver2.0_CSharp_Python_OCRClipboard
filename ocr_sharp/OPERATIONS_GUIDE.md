# ocr_sharp - DPI対応 OCR Clipboard クライアント

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
└── OPERATIONS_GUIDE.md
```

## 特徴
- **DPI 対応**: Windows の表示倍率を 100% に合わせれば座標ズレが起きません。
- **PaddleOCR 日本語モデル**で読み取り精度が高いです。
- **Tkinter（範囲選択） + mss（画面キャプチャ）**の組み合わせで素早く画像を取得します。
- 認識結果は自動的にクリップボードへコピーされ、そのまま貼り付けできます。
- ルート `README.md` では「実運用クライアント」として位置付けています。

## インストール
```pwsh
pip install -r requirements.txt
```

## 実行方法
```pwsh
python main.py
```

## 注意
- DPI スケーリングは必ず 100% にしてください。125% 以上だと座標がずれます。
- サブモニタでは動作保証していません。Display 1 でキャプチャしてください。
- `draw_ocr` で画像に結果を書き込みたい場合は `fonts/NotoSansCJKjp.otf` を配置してください。
- もっと軽いテストをしたい場合は `ocr_app/CLI_SAMPLE_GUIDE.md` を参照してください。

## ライセンス
MIT
