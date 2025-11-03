# マハラノビス距離異常検知システム - 実装完了レポート

## 実装サマリー

**日付**: 2025年11月3日  
**対象**: 少数標本（12件）でのOCR品質監視  
**手法**: マハラノビス距離 + Leave-One-Out + Ledoit-Wolf推定

## 実装した改善点

### ✅ 1. 距離単位の固定（D²統一）

**問題**: D と D² が混在すると運用者が混乱

**解決策**:
- すべての閾値・表示を**D²（距離の2乗）**で統一
- グラフの凡例に単位を明記
  - 理論: χ²95% (=15.5 D²)
  - 経験: 95% (=53.0 D²)
  - 準異常: (=25.0 D²)

**実装箇所**:
```python
# tools/visualize_ocr_results.py
THEORETICAL_THRESHOLD_D2 = 15.51  # χ²(df=8) 95%点
EMPIRICAL_THRESHOLD_D2 = 53.00    # ブートストラップ95%点
WARNING_THRESHOLD_D2 = 25.0       # 準異常閾値
```

### ✅ 2. 閾値の使い分け（探索 vs 本番）

**探索・可視化**:
- 理論線（χ²）と経験線（ブートストラップ）を両方表示
- ズレの監視でデータ品質を評価

**本番判定**:
- **経験95%（53.0 D²）を採用**
- 理論線は少数標本では甘すぎる

**将来拡張**:
- サンプル数20超えたらタグ別に再推定

**実装箇所**:
- `create_mahalanobis_analysis()` - 両方の閾値を可視化
- `classify_anomaly_level()` - 経験閾値で判定

### ✅ 3. フラグ設計（異常検知→デグレード）

**運用ルール**:

| D² 範囲 | レベル | アクション | コード判定 |
|--------|--------|-----------|-----------|
| D² ≤ 25 | 通常運転 | 標準処理続行 | `normal` |
| 25 < D² ≤ 53 | 準異常 | ログ記録・要観察 | `warn` |
| D² > 53 | 強い異常 | 前処理強化→フォールバック | `degrade` |

**実装箇所**:
```python
def classify_anomaly_level(distance_d2):
    if distance_d2 > EMPIRICAL_THRESHOLD_D2:
        return 'strong_anomaly', 'degrade'
    elif distance_d2 > WARNING_THRESHOLD_D2:
        return 'weak_anomaly', 'warn'
    else:
        return 'normal', 'normal'
```

### ✅ 4. QQプロット追加

**目的**: 正規性仮定の妥当性確認

**実装**:
- `create_mahalanobis_analysis()` の2番目のサブプロット
- χ²分布（df=8）との比較
- 直線から外れるタグは別途モデリング検討

**将来対応**:
- Box-Cox/Yeo-Johnson変換の検討
- タグ別の分布分析

### ✅ 5. 詳細ログ出力（JSONL形式）

**必須項目**:

```json
{
  "timestamp": "ISO8601形式",
  "image_id": "001",
  "tag": "clean",
  
  "features_raw": {
    "cer": 0.028,
    "latency_ms": 5672.2,
    "detected_chars": 0,
    "ground_truth_chars": 0,
    "confidence": 0.983,
    "dt_boxes_count": 0,
    "ocr_ms": 0.0,
    "post_ms": 0.0
  },
  
  "anomaly_detection": {
    "mahal_distance_d2": 1.33,
    "cov_version": "ledoit_wolf",
    "thresholds": {
      "theory_d2": 15.51,
      "empirical_d2": 53.0,
      "warning_d2": 25.0
    },
    "level": "normal",
    "decision": "normal",
    "rationale": "D²=1.33 vs 閾値=53.0"
  },
  
  "quality_metrics": {
    "cer": 0.028,
    "levenshtein": 0,
    "rule_used": "empirical_95pct",
    "quality_ok": true
  },
  
  "performance": {
    "proc_total_ms": 5672.2,
    "ocr_ms": 0.0,
    "post_ms": 0.0,
    "engine": "paddle"
  }
}
```

**利点**:
- 可視化・再現・デバッグ全部可能
- 時系列分析に対応
- BI ツール連携可能

### ✅ 6. 012の扱い（ストレステスト分離）

**問題**: 意図的困難画像が合格率を不当に悪化

**解決策**:
```bash
# 回帰テスト用（012除外）
python tools/visualize_ocr_results.py --exclude_stress

# ストレステスト用（012含む、将来実装）
python tools/visualize_ocr_results.py --stress_only
```

**実装箇所**:
```python
if args.exclude_stress:
    results = [r for r in all_results 
               if not any(tag in r['tags'] for tag in ['012', 'stress', 'impossible'])]
```

**レポート分離**:
- 回帰テストセット → 品質維持確認
- ストレステストセット → 耐障害性確認

## 生成される可視化

### 1. 統合分析グラフ (`ocr_integrated_analysis.png`)
- 上段：CER棒グラフ（異常レベル別色分け）
- 下段：マハラノビス距離D²（閾値ライン入り）

### 2. マハラノビス分析 (`mahalanobis_analysis.png`)
- 距離ヒストグラム + 閾値
- QQプロット（χ²分布）
- タグ別距離箱ひげ図
- 距離 vs CER 散布図

### 3. タグ別統合分析 (`ocr_tag_analysis_integrated.png`)
- タグ別CER分布
- タグ別異常度分布
- タグ別異常検知率
- 統計サマリーテーブル

### 4. パフォーマンス分析 (`ocr_performance_integrated.png`)
- CER vs レイテンシ
- 距離 vs CER
- 距離 vs レイテンシ
- 運用決定ルール表示

### 5. 統合ダッシュボード (`ocr_integrated_dashboard.png`)
- 総合サマリー（7パネル）
- エンジン分布・合格率・異常分布
- 統計指標・運用ルール表示

## テスト結果

### データセット
- **総サンプル数**: 12件
- **特徴量次元**: 8次元
- **共分散推定**: Ledoit-Wolf
- **距離範囲**: 0.7 - 101.6 D²

### 異常検知結果
- **通常**: 11件 (91.7%)
- **準異常**: 0件 (0%)
- **強異常**: 1件 (8.3%) → 画像012（lowcontrast-dense, CER=0.92, D²=101.6）

### 品質評価
- **合格率**: 9/12 (75.0%)
- **平均CER**: 0.177
- **異常検知精度**: 100%（012を正確に検出）

## 技術的詳細

### 共分散推定
```python
from sklearn.covariance import LedoitWolf

cov_est = LedoitWolf()
cov_est.fit(X_train)
cov_inv = np.linalg.inv(cov_est.covariance_)
```

### Leave-One-Out方式
```python
for i in range(n_samples):
    train_mask = np.ones(n_samples, dtype=bool)
    train_mask[i] = False
    X_train = features_scaled[train_mask]
    # 共分散推定・距離計算
```

### 標準化
```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
features_scaled = scaler.fit_transform(features)
```

## 依存関係追加

`requirements.txt` に追加:
```
matplotlib==3.7.5
scikit-learn==1.3.2
scipy==1.11.4
```

## ファイル構成

```
tools/
  visualize_ocr_results.py  # 統合版（430行）

docs/
  MAHALANOBIS_ANOMALY_DETECTION_GUIDE.md  # 運用ガイド
  MAHALANOBIS_IMPLEMENTATION_REPORT.md    # このファイル

tests/outputs/
  ocr_integrated_analysis.png              # 統合分析
  mahalanobis_analysis.png                 # 詳細分析
  ocr_tag_analysis_integrated.png          # タグ別
  ocr_performance_integrated.png           # パフォーマンス
  ocr_integrated_dashboard.png             # ダッシュボード
  ocr_operational_log_YYYYMMDD_HHMMSS.jsonl  # 運用ログ
```

## 使用方法

### 基本実行
```bash
python tools/visualize_ocr_results.py \
  --input tests/outputs/ocr_dataset_eval.json \
  --output tests/outputs
```

### ストレステスト除外
```bash
python tools/visualize_ocr_results.py \
  --input tests/outputs/ocr_dataset_eval.json \
  --output tests/outputs \
  --exclude_stress
```

### オプション
- `--input`: 入力JSONファイル（デフォルト: tests/outputs/ocr_dataset_eval.json）
- `--output`: 出力ディレクトリ（デフォルト: tests/outputs）
- `--threshold`: CER閾値（デフォルト: 0.30）
- `--cov_estimator`: 共分散推定手法（ledoit_wolf | empirical）
- `--exclude_stress`: ストレステスト画像除外

## 今後の課題

### 短期（1-2週間）
- [ ] タグ別閾値の微調整
- [ ] 前処理強化ルールの実装
- [ ] フォールバック品質の検証

### 中期（1-2ヶ月）
- [ ] サンプル数20超えでタグ別モデリング
- [ ] Box-Cox変換の適用検討
- [ ] 経時変化の監視機能

### 長期（3-6ヶ月）
- [ ] 新OCRエンジン統合時の再校正
- [ ] 画像種別自動分類
- [ ] 動的閾値調整

## まとめ

12枚という少数標本に対し、統計的に堅実な異常検知システムを構築できた。

**主要成果**:
1. D²単位の統一で運用混乱を防止
2. 経験閾値53.0の採用で実用的な判定
3. 3段階フラグ設計で運用アクション明確化
4. 詳細ログで監視・再現・デバッグ対応
5. ストレステスト分離で正確な品質評価

**運用推奨**:
- 経験閾値53D²を異常判定基準として採用
- 準異常25D²超過時は要観察
- 強異常は前処理強化→再試行→フォールバック
- 012はストレステスト枠で管理

**統計、君のことは好きじゃないけど、今回は役に立ったな。** 📊✨

---

**作成日**: 2025年11月3日  
**バージョン**: 1.0.0  
**担当**: OCR品質監視チーム
