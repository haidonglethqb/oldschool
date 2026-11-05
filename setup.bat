@echo off
chcp 65001 >nul
title Old School - Setup A-Z
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
if errorlevel 1 (
    echo(
    echo ======================================================================
    echo [LOI] Qua trinh cai dat hoac khoi dong gap su co.
    echo Cua so lenh duoc giu lai de ban co the xem thong bao loi o tren.
    echo ======================================================================
    pause
    exit /b 1
)
exit /b 0
