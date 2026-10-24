@echo off
chcp 65001 >nul
title Old School - Web Server (http://127.0.0.1:8000)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [!] Chua tim thay moi truong .venv. Dang chay setup.bat tu dong...
    call "%~dp0setup.bat"
    exit /b %ERRORLEVEL%
)

echo ======================================================================
echo   OLD SCHOOL - DANG CHAY WEB SERVER TAI: http://127.0.0.1:8000/
echo   (Nhan Ctrl+C de dung server)
echo ======================================================================
start "" "http://127.0.0.1:8000/"
".venv\Scripts\python.exe" manage.py runserver 8000
