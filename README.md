OCR Clipboard v2.0 — C# + Python IPC Skeleton

Overview
- C# console app hosts a Python worker via a simple JSON-over-stdio IPC.
- DTOs are mirrored between C# and Python.
- Envelope: newline-delimited JSON. Fields: `id`, `type`, `payload`.

Message Types
- `health.check` -> respond with `health.ok`
- `ocr.perform` -> respond with `ocr.result` (stubbed)
- `error` for failures

Quick Start
1) Ensure Python is available as `python` and .NET SDK is installed.
2) From repo root, run the C# app (it will start Python worker automatically):
   - `dotnet run --project src/csharp/OCRClipboard.App`

Project Structure
- `src/csharp/OCRClipboard.App` — C# console app, DTOs, and IPC client
- `src/python/ocr_worker` — Python worker, DTOs, and handlers

Notes
- The C# host sets `PYTHONPATH` to `src/python` so the module `ocr_worker` is importable.
- The Python worker is unbuffered (`-u`) to flush output promptly.

