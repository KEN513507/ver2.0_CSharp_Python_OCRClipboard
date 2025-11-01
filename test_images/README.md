# テスト画像ディレクトリ

## 📋 概要

このディレクトリには、`--test-image` モードで使用する**実際のスクリーンショット画像**を配置します。

従来のベンチマークは理想的条件（人工的なテキスト、白背景、14ptメイリオ）でのテストでしたが、このディレクトリに配置する画像は**実際の使用状況を反映した現実的なテスト**のために使用されます。

## 🚀 クイックスタート

**初めて画像テストを実施する方へ:**

👉 **完全な実施ガイド:** [docs/IMAGE_TEST_GUIDE.md](../docs/IMAGE_TEST_GUIDE.md)

1. **DPIスケーリングを100%に設定**（必須）
2. **Webページや文書のスクリーンショットを撮影**
3. **このディレクトリに保存**（PNG/JPG形式）
4. **テスト実行**

詳しい手順は上記のガイドを参照してください。

---

## ディレクトリ構成

```
test_images/
  ├── README.md                    # このファイル
  ├── sample_100chars.png          # 100文字程度のテスト画像
  ├── sample_100chars.txt          # 100文字の期待テキスト
  ├── sample_500chars.png          # 500文字程度のテスト画像
  ├── sample_500chars.txt          # 500文字の期待テキスト
  ├── sample_1000chars.png         # 1000文字程度のテスト画像
  ├── sample_1000chars.txt         # 1000文字の期待テキスト
  ├── real_webpage_1000chars.png   # 実際のWebページキャプチャ
  ├── real_webpage_1000chars.txt   # Webページの期待テキスト
  └── ...
```

---

## 使い方

### 1. 画像とテキストを準備

#### 方法A: 自動生成（簡易テスト）
```pwsh
# ベンチマークモードで生成された画像を保存
dotnet run --project src\csharp\OCRClipboard.App -- --benchmark
# → outputs/ocr_benchmark.png が生成される
```

#### 方法B: 実際のスクリーンショット（推奨）
1. ブラウザでWebページを開く
2. 矩形選択ツール（Snipping Tool等）でキャプチャ
3. `test_images/` に保存
4. 期待テキストを `.txt` ファイルとして保存

**期待テキストの作り方**:
```pwsh
# Webページのテキストをコピペして保存
"これはテストテキストです。..." | Out-File -Encoding UTF8 test_images/sample.txt
```

---

### 2. 自動テスト実行

#### 基本実行（識字率検証なし）
```pwsh
dotnet run --project src\csharp\OCRClipboard.App -- --test-image test_images/sample_500chars.png
```

**出力例**:
```
[OCR実行] 5回測定開始...
  試行1: 250.3ms, fragments=50, 文字数=480
  試行2: 245.1ms, fragments=50, 文字数=482
  ...
[統計結果]
処理時間: 平均=248.5ms, 最小=245.1ms, 最大=255.0ms
```

---

#### H0棄却判定付き（期待テキスト指定）
```pwsh
dotnet run --project src\csharp\OCRClipboard.App -- --test-image test_images/sample_1000chars.png test_images/sample_1000chars.txt
```

**出力例**:
```
[OCR実行] 5回測定開始...
  試行1: 850.3ms, fragments=100, 識字率=98.50%
  試行2: 845.1ms, fragments=100, 識字率=98.70%
  ...
[統計結果]
処理時間: 平均=848.5ms, 最小=845.1ms, 最大=855.0ms
識字率: 平均=98.60%, 最小=98.50%

[H0判定]
  処理時間 < 10,000ms: ✅ 受容 (最大=855.0ms)
  識字率 >= 95%: ✅ 受容 (最小=98.50%)

🟢 結論: H0を受容（Windows.Media.Ocrは実用範囲内）
```

---

### 3. H0棄却を狙うテストケース

**目標**: 処理時間 >= 10,000ms または 識字率 < 95% を観測する

#### 戦略1: 超長文テスト
```pwsh
# 2000文字以上の画像でテスト
dotnet run --project src\csharp\OCRClipboard.App -- --test-image test_images/real_2000chars.png test_images/real_2000chars.txt
```

#### 戦略2: 複雑なレイアウト
- 小フォント（<10pt）
- 複数カラムレイアウト
- 装飾フォント（明朝体、斜体等）

#### 戦略3: 低品質画像
- 低解像度（DPI < 100%）
- ノイズ多数
- 傾き・歪み

---

## テスト画像作成ガイドライン

### 良いテストケース
- ✅ **実際の使用シーン**: Webページ、PDF、アプリUI
- ✅ **文字数の多様性**: 100, 500, 1000, 1500, 2000文字
- ✅ **フォントの多様性**: ゴシック、明朝、等幅
- ✅ **レイアウトの多様性**: 1段組、2段組、表組み

### 避けるべきケース
- ❌ **人工的すぎる**: 単色背景に黒文字だけ
- ❌ **繰り返しテキスト**: 「テストテストテスト...」
- ❌ **理想的すぎる**: フォント14pt、行間広め、白背景

---

## CI/CD連携

GitHub Actionsでテスト実行：

```yaml
- name: OCR Image Test
  run: |
    dotnet run --project src/csharp/OCRClipboard.App -- --test-image test_images/sample_500chars.png test_images/sample_500chars.txt
```

---

## トラブルシューティング

### 画像が読み込めない
```
❌ エラー: 画像ファイルが見つかりません: test_images/xxx.png
```
→ ファイルパスを確認（絶対パスまたは相対パス）

### 識字率が期待値と大きく異なる
```
識字率: 平均=50.00%
```
→ 期待テキストが画像と一致しているか確認

### 処理時間が異常に長い
```
処理時間: 平均=15000.0ms
```
→ **H0棄却成功！** これが目標です

---

## まとめ

| モード | 用途 | コマンド |
|--------|------|---------|
| 簡易テスト | 処理時間のみ計測 | `--test-image <画像>` |
| H0判定 | 処理時間 + 識字率検証 | `--test-image <画像> <期待テキスト>` |

**推奨ワークフロー**:
1. 実際のWebページをキャプチャ（1000文字前後）
2. テキストを手動でコピー → `.txt` 保存
3. `--test-image` で自動テスト実行
4. H0棄却されるまで文字数を増やす（1500, 2000, 2500...）
