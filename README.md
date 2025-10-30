dotnet run --project src/csharp/OCRClipboard.App

OCR Clipboard v2.0  IPC Skeleton

Overview
- C#コンソールアプリがPython OCRワーカーをJSON-over-stdio IPCで起動・連携。
- DTOはC#・Pythonでミラー定義。

【OCR判定ロジック追加】
OCR結果は「想定されるテキスト」と比較し、信頼度（confidence）閾値を用いて判定します。
誤認・誤差判定は品質制約（最大4文字以内）と信頼度閾値の両方で管理します。
このロジックはOCR品質・要件定義にも適用されます。


- OCR結果・誤差はすべてログ出力し、品質管理。

【非要件定義（現状対応しない範囲）】
- ディスプレイ2（拡張画面）での正確な矩形選択・座標補正は未対応。
- 仮想デスクトップ・複数ディスプレイの座標ズレ解消は今後の課題。
- GPU高速化・NamedPipe/gRPC IPCは将来対応予定。

【現状の運用・注意点】
- プライマリディスプレイ（ディスプレイ1）でのみOCR品質を担保。
- 複数ディスプレイ環境では主画面のみ正確なOCR範囲選択が可能。
- 拡張画面でのズレ・誤認は現状仕様。今後改善予定。

Quick Start
1) Python（`python`）と.NET SDKをインストール。
2) repo rootからC#アプリを起動（Pythonワーカー・オーバーレイも自動起動）:
   - `dotnet run --project src/csharp/OCRClipboard.App`

# 実行方法（推奨）

```pwsh
# repo root から実行
cd C:\Users\user\Documents\Projects\ver2.0_C#+Python_OCRClipboard
dotnet run --project src/csharp/OCRClipboard.App
```

- キャプチャ画像は `logs/debug_capture.png` に保存されます（どこから実行しても一貫）。

Project Structure
- `src/csharp/OCRClipboard.App` — C# console app, DTOs, and IPC client
- `src/csharp/OCRClipboard.Overlay` — WPF overlay (single monitor), selection → PNG capture (GDI fallback)
- `src/python/ocr_worker` — Python worker, DTOs, and handlers

Notes
- C#ホストは`PYTHONPATH`を`src/python`に設定し、`ocr_worker`モジュールをimport可能に。
- Pythonワーカーは`-u`（アンバッファ）で即時出力。
- オーバーレイ・選択は常に主画面の物理ピクセル座標で動作。

---
## 現状の課題・注意点

- ディスプレイ1（主画面）では矩形選択範囲が正確にOCR可能。
- ディスプレイ2（拡張画面）では選択範囲が大きくズレる現象あり。
- 原因は座標系・DPI・仮想スクリーンの扱い。
- 今後、複数ディスプレイでも正確な範囲指定ができるよう修正予定。
- この注意書きは課題解決後に削除してください。

## OCR機能について

- **現状はプライマリ画面のみ対応、セカンダリ画面は今後検討予定。**
- OCR精度向上のため、画像前処理（リサイズ・ノイズ除去・適応的閾値処理）と品質判定（文字誤差5文字以内、信頼度0.8以上）を導入。
- 品質判定に不合格の場合、ログに誤差情報を出力。
- OCRエンジンとしてyomitokuを使用し、認識結果の誤差パターンを分析可能。
- テストパターン・実画像でのOCR精度検証は100%/125%/150%スケールで実施。

---
