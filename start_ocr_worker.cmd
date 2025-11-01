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

REM CPU Performance Tuning (ChatGPT recipe for i7-8550U 4C8T)
REM Reduce thread contention and improve inference speed
set OMP_NUM_THREADS=2
set MKL_NUM_THREADS=2
set KMP_AFFINITY=disabled
set KMP_BLOCKTIME=0

REM Force mobile models for CPU performance (server models too heavy: 82s vs target 3-8s)
REM ocr.py now forces mobile models via use_angle_cls=False and auto-download
set OCR_PROFILE=mobile
set OCR_CPU_THREADS=2
set OCR_REC_BATCH_NUM=6

REM For manual mobile model setup (if downloaded):
REM set OCR_DET_DIR=C:\Users\user\.paddlex\official_models\PP-OCRv5_mobile_det
REM set OCR_REC_DIR=C:\Users\user\.paddlex\official_models\PP-OCRv5_mobile_rec

REM Optional: Idle timeout in seconds (14400 = 4 hours)
set IDLE_EXIT_SEC=14400

REM Start worker in resident mode
echo [INFO] Starting OCR worker in resident mode...
echo [INFO] OCR_PROFILE=%OCR_PROFILE%
echo [INFO] CPU threads: OMP=%OMP_NUM_THREADS% MKL=%MKL_NUM_THREADS%
echo [INFO] IDLE_EXIT_SEC=%IDLE_EXIT_SEC%
echo [INFO] Press Ctrl+C to stop
python -m ocr_worker.main --mode resident

pause
