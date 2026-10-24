@echo off
chcp 65001 >nul
title Old School - Setup A-Z
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
exit /b %ERRORLEVEL%
