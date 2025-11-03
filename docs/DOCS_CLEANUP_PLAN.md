# ドキュメント整理計画（2日完成版）

## 残すドキュメント（最小限）

### 必須（ユーザー向け）
1. `README.md` - クイックスタート（実行方法のみ）
2. `PROJECT_SPEC.md` - 品質閾値・制約・仕様

### 必須（開発者向け）
3. `docs/OCR_TEST_SET1_PLAN.md` - テストセット説明
4. `docs/MAHALANOBIS_ANOMALY_DETECTION_GUIDE.md` - 異常検知運用ガイド

---

## 削除・統合するドキュメント

### 統合先: `PROJECT_SPEC.md`
- `FACTORY_IMPROVEMENTS.md` → 品質要件セクションに統合
- `docs/OCR_PERFORMANCE_MONITOR.md` → 監視仕様セクションに統合

### 削除（古い分析レポート）
- `docs/ocr_overfit_analysis_20251102.md` → 最終テスト結果で置き換え
- `docs/ocr_quality_report_20251029.md` → 古い
- `docs/requirements_trace_20251102.md` → TODO.mdに統合済み

### アーカイブ（参考用）
- `docs/MAHALANOBIS_IMPLEMENTATION_REPORT.md` → 詳細な実装ログ（開発者向け）
- `docs/DOCUMENTATION_NAV.md` → ドキュメントマップ（中規模以上で有用）

---

## 新規作成（2日で完成）

### `PROJECT_SPEC.md` 構成
```markdown
# OCRClipboard プロジェクト仕様書

## 1. システム概要
- 目的・機能

## 2. 品質要件
- CER閾値: 0.30（合格ライン）
- 信頼度閾値: 0.7
- 合格率目標: 83%以上（12枚中10枚）

## 3. 制約事項
- Primary Display専用
- DPIスケール: 100%, 125%, 150%のみ検証済み

## 4. テスト仕様
- Set1テストセット（12枚）
- タグ定義（clean, dense, small, large, lowcontrast, mono-code）
- ストレステスト（012: lowcontrast-dense）

## 5. 異常検知
- マハラノビス距離
- 閾値: warn=18D², degrade=26D²

## 6. 運用ガイド
- 実行方法
- ログ確認方法
- トラブルシューティング
```

---

## 実行順序

### Day 1 終了後
1. `PROJECT_SPEC.md`作成（1h）
2. 古いドキュメント削除

### Day 2 終了後
3. `README.md`簡略化
4. 最終テスト結果を`docs/`に追加
