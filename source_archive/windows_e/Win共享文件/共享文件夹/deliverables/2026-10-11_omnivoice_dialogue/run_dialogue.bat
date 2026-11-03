@echo off
setlocal
set "UI_PY=%~dp0..\..\.venv-live\Scripts\python.exe"
if not exist "%UI_PY%" (
  echo Configure Python paths using launch.py. See README.md.
  pause
  exit /b 1
)
"%UI_PY%" -B "%~dp0launch.py" %*
if errorlevel 1 pause
endlocal
