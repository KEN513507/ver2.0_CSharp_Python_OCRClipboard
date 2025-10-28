OCR Clipboard v2.0 — C# + Python IPC Skeleton

Overview
- C# console app hosts a Python worker via a simple JSON-over-stdio IPC.
- DTOs are mirrored between C# and Python.
- Envelope: newline-delimited JSON. Fields: `id`, `type`, `payload`.

Fixed Specs (No "Virtual Desktop" concept)
- Target monitor only: choose monitor under mouse via `GetCursorPos` → `MonitorFromPoint`.
- Coordinates: always monitor-local physical pixels. Origin (0,0) is the chosen monitor's top-left.
- Overlay: borderless, semi-transparent, topmost, toolwindow. Styles: `WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW`.
- Selection: drag to create rectangle, ESC cancels, mouse-up/Enter confirms.
- Capture: stubbed with GDI BitBlt one-shot (for now). Future: Windows.Graphics.Capture + GPU crop.
- Output: send cropped image to OCR backend (currently over stdio as base64; future Named Pipe/gRPC). Copy OCR text to clipboard.

Message Types
- `health.check` -> respond with `health.ok`
- `ocr.perform` -> respond with `ocr.result` (stubbed)
- `error` for failures

Quick Start
1) Ensure Python is available as `python` and .NET SDK is installed.
2) From repo root, run the C# app (it starts Python worker and overlay):
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
- The C# host sets `PYTHONPATH` to `src/python` so the module `ocr_worker` is importable.
- The Python worker is unbuffered (`-u`) to flush output promptly.
 - The overlay and selection operate strictly in monitor-local physical pixel coordinates.

---

## 現状の課題・注意点

- ディスプレイ1（主画面）では矩形選択範囲が正確にOCR可能。
- ディスプレイ2（拡張画面）では選択範囲が大きくズレる現象あり。
- 原因は座標系・DPI・仮想スクリーンの扱い。
- 今後、複数ディスプレイでも正確な範囲指定ができるよう修正予定。
- この注意書きは課題解決後に削除してください。

---
