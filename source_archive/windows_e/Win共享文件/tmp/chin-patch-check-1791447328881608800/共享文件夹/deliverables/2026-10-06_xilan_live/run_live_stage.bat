@echo off
setlocal
set "SHARED_ROOT=%~dp0..\.."
set "PY=%AURA_PYTHON%"
if not defined PY if exist "%SHARED_ROOT%\.venv-live\Scripts\python.exe" set "PY=%SHARED_ROOT%\.venv-live\Scripts\python.exe"
if not defined PY if exist "%SHARED_ROOT%\..\tmp\aura-validation-venv\Scripts\python.exe" set "PY=%SHARED_ROOT%\..\tmp\aura-validation-venv\Scripts\python.exe"
if not defined PY (
  echo Python runtime missing. Follow the migration handover to create .venv-live.
  pause
  exit /b 1
)
"%PY%" -B "%SHARED_ROOT%\aura\tools\realtime_stage.py" --root "%~dp0." %*
if errorlevel 1 pause
endlocal
