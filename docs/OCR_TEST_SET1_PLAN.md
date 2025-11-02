# OCR Test Set 1 – Short Plan

テストセット set1 を作るときはこの 3 ステップだけ覚えておけば OK です。詳細は `docs/DOCUMENTATION_NAV.md` から補足を辿れます。

## 1. 自動生成コマンド
```powershell
pip install beautifulsoup4 pillow           # 初回のみ
pwsh tools/build_set1.ps1 -Html ocr_test_set1_corpus_corrected.html
```
出力: `test_images/set1/` に `.txt` / `.png` / `manifest.csv` が 12 ケース分並ぶ。

## 2. スポットチェック
- `.txt` … HTML の元文と差がないか 2〜3 件見る
- `.png` … タグごとの見た目（small / invert / tilt2 など）を軽く確認
- `manifest.csv` … 行数が 12、文字数カラムが妥当か

## 3. 保存と共有
```powershell
git add test_images/set1/*
git commit -m "Add OCR test set 1"
git push
```

### 補足リンク
- スクリプト解説: `tools/` 各ファイル
- 改善履歴: `FACTORY_IMPROVEMENTS.md`
- 生成データの使い方: `tests/scripts/test_ocr_accuracy.py`
