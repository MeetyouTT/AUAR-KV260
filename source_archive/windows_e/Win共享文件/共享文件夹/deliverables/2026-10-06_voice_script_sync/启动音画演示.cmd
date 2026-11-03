@echo off
cd /d "%~dp0"
echo Open http://127.0.0.1:8771/
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_preview.ps1"
if errorlevel 1 pause
