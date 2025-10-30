
# TODO統合リスト（2025-10-31）

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
