@echo off
echo ========================================
echo ATC Transcription Tool - Installation
echo ========================================
echo.

echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo Python found!
echo.

echo Installing required packages...
pip install PyQt5
if %errorlevel% neq 0 (
    echo ERROR: Failed to install PyQt5
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Desktop app (PyQt):
echo   python atc_transcription_app.py
echo   Or double-click run_app.bat
echo.
echo Optional web UI (Flask): cd webapp ^&^& run_webapp.bat
echo   Bind defaults to 127.0.0.1. Do not enable FLASK_DEBUG or expose the port
echo   on a shared network — the debugger is unsafe when reachable remotely.
echo.
pause
