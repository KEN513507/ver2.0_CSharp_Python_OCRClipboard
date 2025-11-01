# 品質ヒューリスティック検証メモ

Python 版で実証済みの判定式:
- 誤差距離 <= min(25% of expected length, 20 文字)
- 文字列長 (normalized actual) >= max(1, expected length * 0.25)
- アルファ数 / 文字数 >= 0.5
- (文字数 >= 5 の場合) confidence >= 0.70

C# 版では `QualityConfig` と `OcrQualityEvaluator.IsAcceptable` に移植済み。

テスト: `tests/Quality/QualityEvaluatorTests.cs`
- NFKC / IgnoreCase の ON/OFF
- 環境変数による閾値上書き
