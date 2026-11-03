@echo off
rem =========================================================================
rem Wait for batch_v2_states.bat to finish (ALL_DONE in %TEMP%\aura_v2_batch.log),
rem then run the three-layer acceptance checks automatically.
rem Pure ASCII + CRLF only (see docs: v2 implementation record, section 4).
rem =========================================================================
set AU=%~dp0..
set PY=D:\sd-webui-aki-v4.11.1-cu128\ComfyUI_Windows_portable_cu130.7z\ComfyUI_Windows_portable\python_standalone\python.exe
set B=%TEMP%\aura_v2_batch.log
set T=%TEMP%

:wait
findstr /C:"ALL_DONE" "%B%" >nul 2>&1
if errorlevel 1 (
  timeout /t 60 /nobreak >nul
  goto wait
)

echo === verify amp/loop/size === > "%T%\aura_v2_verify.log"
"%PY%" -s "%AU%\tools\verify_v2_amp.py" >> "%T%\aura_v2_verify.log" 2>&1
echo === verify green stability (IDLE tag) === >> "%T%\aura_v2_verify.log"
"%PY%" -s "%AU%\tools\verify_green_stab.py" "%T%\aura_green_v2\IDLE" >> "%T%\aura_v2_verify.log" 2>&1
echo === VERIFY ALL DONE === >> "%T%\aura_v2_verify.log"
