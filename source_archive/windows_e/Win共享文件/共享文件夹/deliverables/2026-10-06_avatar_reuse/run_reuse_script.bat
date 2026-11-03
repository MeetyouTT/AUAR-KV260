@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_reuse_script.ps1"
if errorlevel 1 pause
