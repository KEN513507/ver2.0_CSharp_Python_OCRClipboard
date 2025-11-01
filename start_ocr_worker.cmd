@echo off
REM Desktop launcher for resident OCR worker
REM Double-click this to start the worker in resident mode

setlocal
cd /d %~dp0

REM Activate virtual environment
call .venv_clean\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate .venv_clean
    pause
    exit /b 1
)

REM Set Python module paths
set PYTHONPATH=.;src\python;ocr-screenshot-app

REM Use server model (mobile model selection currently not working via Python API)
REM Mobile models would need manual download and OCR_DET_DIR/OCR_REC_DIR specification
set OCR_PROFILE=server

REM For manual mobile model setup (if downloaded):
REM set OCR_DET_DIR=C:\Users\user\.paddlex\official_models\PP-OCRv5_mobile_det
REM set OCR_REC_DIR=C:\Users\user\.paddlex\official_models\PP-OCRv5_mobile_rec

REM Optional: Set CPU threads (default 4)
set OCR_CPU_THREADS=4

REM Optional: Idle timeout in seconds (14400 = 4 hours)
set IDLE_EXIT_SEC=14400

REM Start worker in resident mode
echo [INFO] Starting OCR worker in resident mode...
echo [INFO] OCR_PROFILE=%OCR_PROFILE%
echo [INFO] IDLE_EXIT_SEC=%IDLE_EXIT_SEC%
echo [INFO] Press Ctrl+C to stop
python -m ocr_worker.main --mode resident

pause
