@echo off
setlocal
cd /d "%~dp0\.."
set "AURA_FRAMEWORK_PY=python"
if exist ".venv\Scripts\python.exe" set "AURA_FRAMEWORK_PY=.venv\Scripts\python.exe"
if "%~1"=="" (
  "%AURA_FRAMEWORK_PY%" -s tools\aura_project.py demo
  pause
) else (
  "%AURA_FRAMEWORK_PY%" -s tools\aura_project.py %*
  if errorlevel 1 pause
)
endlocal
