@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_script_window.ps1" -Voice silent
if errorlevel 1 pause
