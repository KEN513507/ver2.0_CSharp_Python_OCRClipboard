# test_images/ - テスト画像ディレクトリ

## 📋 このディレクトリについて

`--test-image` モードで使用する**実際のスクリーンショット画像**を配置します。

---

## � 完全なテストガイド

👉 **[docs/IMAGE_TEST_GUIDE.md](../docs/IMAGE_TEST_GUIDE.md)** を参照してください。

以下の内容が含まれています：
- ✅ 準備するもの（DPI設定、画像撮影方法）
- ✅ 詳細な実施手順（ステップ1-3）
- ✅ テストケーステンプレート
- ✅ トラブルシューティング
- ✅ テスト結果記録フォーマット

---

## 🚀 クイックスタート

```pwsh
# 1. DPIスケーリングを100%に設定（必須）

# 2. スクリーンショットをこのディレクトリに保存

# 3. テスト実行
dotnet run --project src\csharp\OCRClipboard.App -- --test-image test_images/your_image.png

# 4. 精度も測定する場合（期待テキストファイルも用意）
dotnet run --project src\csharp\OCRClipboard.App -- --test-image test_images/your_image.png test_images/your_image.txt
```

---

## 📂 推奨ディレクトリ構成

```
test_images/
├── QUICK_START.md               # このファイル
├── sample_100chars.png          # 100文字程度のスクリーンショット
├── sample_100chars.txt          # 期待テキスト（オプション）
├── sample_500chars.png          # 500文字程度のスクリーンショット
├── sample_500chars.txt
├── sample_1000chars.png         # 1000文字程度のスクリーンショット
├── sample_1000chars.txt
└── sample_2000chars.png         # 2000文字（H0棄却テスト用）
    └── sample_2000chars.txt
```

---

## ⚠️ 注意事項

- **DPIスケーリング**: 必ず100%に設定
- **ディスプレイ**: Display 1（プライマリモニター）のみ対応
- **画像形式**: PNG または JPG
- **文字エンコーディング**: 期待テキストファイルはUTF-8で保存

---

## 📖 関連ドキュメント

- **[完全なテストガイド](../docs/IMAGE_TEST_GUIDE.md)** - 詳細な実施手順とトラブルシューティング
- **[プロジェクトREADME](../README.md)** - プロジェクト全体の説明
- **[ベンチマーク結果](../docs/BENCHMARK.md)** - 性能測定データ
