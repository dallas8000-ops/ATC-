@echo off
REM Flask development server — localhost only by default (see FLASK_HOST).
REM SECURITY: Do not set FLASK_DEBUG=1 or expose the port on untrusted networks;
REM           Werkzeug's debugger allows remote code execution if reachable.
echo.
echo ATC Web UI (Flask)
echo - Default: http://127.0.0.1:5000  debug=OFF
echo - Dev reload: set FLASK_DEBUG=1 before running (localhost only)
echo.
cd /d "%~dp0"
python app.py
pause
