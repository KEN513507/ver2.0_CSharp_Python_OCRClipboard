# OCR Quality Improvement Tasks - 2日完成プラン
#　TODOタスク（2025-11-03 → 2025-11-05）

## 完成定義
✅ PaddleOCR 2.7で12枚テストセット全体の品質が安定  
✅ マハラノビス距離による異常検知が動作  
✅ 最低限の運用ドキュメントが揃っている  

---

## 🎯 Day 1 (2025-11-04) - 品質安定化

### 必須タスク
- [ ] **mono-code判定とENモデル自動切り替え** (2h)
  - 画像008のCER改善（0.279 → 0.1以下目標）
  - Box-Drawing文字除外
  - `src/python/ocr_worker/handler.py`に実装
  
- [ ] **lowcontrast系の前処理強化** (2h)
  - 画像012対策（CER=0.92は諦めるがログに記録）
  - CLAHE適用
  - 閾値調整は最小限

- [ ] **品質閾値の最終決定** (1h)
  - CER閾値: 0.30（現状維持 or 0.25に調整）
  - 信頼度: 0.7（現状維持）
  - エラー文字数: 実測値ベースで決定

### 完了条件
- 12枚中10枚以上が合格（83%以上）
- mono-code（008）が改善
- テスト実行とレポート更新

---

## 🎯 Day 2 (2025-11-05) - 運用準備

### 必須タスク
- [ ] **マハラノビス距離の経験閾値確定** (1h)
  - ブートストラップで再推定（簡易版）
  - 閾値を`tools/visualize_ocr_results.py`に反映

- [ ] **ストレステスト分離の完成** (30min)
  - `--stress_only`フラグ追加
  - 012を明示的にストレステスト扱い

- [ ] **運用ドキュメント最終整備** (1.5h)
  - `README.md`をシンプルに（実行方法のみ）
  - `PROJECT_SPEC.md`に品質閾値・制約を明記
  - 不要なドキュメント削除

- [ ] **最終テスト＆PR準備** (1h)
  - 全テスト実行
  - コミットメッセージ整理
  - PR説明文作成

### 完了条件
- テスト通過率83%以上
- ドキュメントが最小限で分かりやすい
- PRがマージ可能状態

---

## Recently Completed (2025-11-03)
- [x] Automated test set creation (`tools/build_set1.ps1`)
- [x] Mahalanobis distance anomaly detection system
  - D² unit standardization (proper covariance calculation)
  - Leave-One-Out + Ledoit-Wolf estimation (n=12)
  - 5 visualization types + operational logs (JSONL)
- [x] Bug fix: Removed incorrect StandardScaler preprocessing
- [x] Documentation: `MAHALANOBIS_ANOMALY_DETECTION_GUIDE.md`, `MAHALANOBIS_IMPLEMENTATION_REPORT.md`

---

## ❌ スコープ外（今回やらない）

### 将来拡張（v2.1以降）
- タグ別モデリング（サンプル数が増えてから）
- 動的閾値調整
- 時系列監視
- ランタイム統合（リアルタイム異常検知）
- 前処理強化パイプライン（自動リトライ）
- フォールバックOCRエンジン

### 理由
- サンプル数12では統計的に不安定
- 2日で実装・検証する時間がない
- 現時点で実運用に必須ではない

---

## 削除予定ファイル（整理）
- [ ] `FACTORY_IMPROVEMENTS.md` → `PROJECT_SPEC.md`に統合
- [ ] `TEST_FAILURES.md` → 最新テスト結果で上書き
- [ ] `PROJECT_TODO_DPI.txt` → `TODO.md`に統合済み
- [ ] 古いログファイル（logs/*.jsonl）→ 最新のみ残す

---

## 参考: TODO統合リスト（2025-10-31）

## 目的：ファイルの可用性・完全性・整合性の向上

### 1. OCRコア・品質・座標・DPI関連
- [x] 画像パス修正（絶対パス化、main.py/ocr_worker/main.py）
- [x] API修正（ocr.ocr→ocr.predict、use_angle_cls→use_textline_orientation）
- [ ] 画像前処理強化（handler.py、フィルタ追加・サンプル画像テスト）
- [ ] OCRパラメータ調整（PaddleOCR設定・言語モデル最適化）
- [ ] stdin/IPC処理強化（空行無視・JSONエラー処理）
- [ ] judge_quality厳格化（エラー検出・制約追加）
- [ ] 品質判定追加制約（英数字比率・長さチェック等）
- [ ] DPIスケール取得・検証
- [ ] 座標変換ロジック分離
- [ ] OverlayWindowの矩形選択補正
- [ ] GraphicsCaptureItemのtransform確認
- [ ] JsonRpcClientの座標受け渡し検証
- [ ] Direct3DDevice生成のモニター依存性調査
- [ ] HMONITOR列挙・選択ロジックのテスト
- [ ] セカンダリ画面の黒画像・白線原因特定
- [ ] capture_diagnostics.jsonl出力実装
- [ ] TEST-A1中央表示の自動検証
- [ ] DPI/座標/セカンダリディスプレイ対応
- [ ] パフォーマンス最適化（10秒未満）
- [ ] タイムアウト・フォールバック追加

### 2. ログ・エラー・テスト・ドキュメント
- [ ] 構造化ログ設計
- [ ] OCR結果の誤差ログ出力
- [ ] 詳細なOCRエラーログ・パターン分析
- [ ] 誤認識パターンの可視化ログ
- [ ] run_all_coordinate_tests.ps1のシナリオ分岐強化
- [ ] run_all_coordinate_tests.ps1の自動判定追加
- [ ] テストパターンHTMLのズレ可視化強化
- [ ] 全体リファクタリング・コード整理
- [ ] 依存（mss, pyperclip）インストール
- [ ] テスト修正（mock・期待値更新）
- [ ] OCR精度テスト（DPI 100/125/150%）
- [ ] README/PROJECT_SPECの現状・制限明記

### 3. 進捗・運用
- [x] 画像パス・API修正済み→日本語OCR安定動作
- [ ] 次：前処理・品質判定・座標/拡張系強化

