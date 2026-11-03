@echo off
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0start_inference.ps1"
if errorlevel 1 (
  echo Model service startup failed. Check the project runtime dashboard.
  pause
  exit /b 1
)
