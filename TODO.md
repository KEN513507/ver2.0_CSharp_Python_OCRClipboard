# TODO統合リスト（2025-11-01 更新）

## 現状：Windows.Media.Ocr 版への移行完了

**アーキテクチャ変更**: PaddleOCR（Python）→ Windows.Media.Ocr（C#単体）

### 完了事項 ✅
- [x] Windows.Media.Ocr エンジン実装（日本語対応、100ms以下）
- [x] Display 1（プライマリモニター）限定のオーバーレイ
- [x] クロップ妥当性チェック（高さ<40px、幅/高さ>25 で警告）
- [x] 上下8pxパディング追加（下端欠け対策）
- [x] 言語初期化診断（日本語以外で警告）
- [x] 固定フォーマット運用ログ（[PERF]/[OCR]/[CLIPBOARD]）
- [x] 3回連続実行で性能検証（OCR: 72-155ms）

### 次のステップ 🎯
1. **トレイ常駐化**
   - [ ] System.Windows.Forms.NotifyIcon 実装
   - [ ] ホットキー登録（Win32 RegisterHotKey、例: Ctrl+Shift+O）
   - [ ] ESCキーで終了
   - [ ] ホットキー衝突検知＆自動フォールバック

2. **品質向上（任意）**
   - [ ] クリップボード二重書き込み抑制（0.5秒間同一テキスト無視）
   - [ ] 最小長・記号比率ヒューリスティック（QualityConfig軽量版）

3. **ドキュメント整備**
   - [x] README更新（Windows.Media.Ocr版の性能データ反映）
   - [x] TODO更新（完了項目整理）
   - [ ] PROJECT_SPEC更新（DFD簡略化、C#単体構成へ）

---

## 追加の検討項目（次ステップ）
- [ ] DTOでの QualityConfig 上書き（優先度: DTO > ENV > 既定）
- [ ] 適用中の QualityConfig をログに1行出力（運用可視化）
- [ ] _mock_paddleocr の適用範囲の明確化（必要なら slow 時は無効化）
- [ ] キャプチャ座標のE2Eテスト（DPI/複数ディスプレイ）
