@echo off
setlocal

echo ============================================
echo   File Encryption Tool - Starting up
echo ============================================

REM Create a virtual environment on first run only
if not exist "venv\" (
    echo Setting up environment for the first time, this may take a minute...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install --upgrade pip >nul
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo Launching app - your browser will open automatically...
python app.py

pause