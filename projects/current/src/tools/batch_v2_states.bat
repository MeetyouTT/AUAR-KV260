@echo off
rem =========================================================================
rem v2 doll asset batch (12 states): generate then ingest, safe to run long.
rem   generate: tools\run_doll_green.py (39 frames / burst 22 / steps 8)
rem   ingest  : tools\aura_ingest_v2.py (matting + A/D1 despill + fit-budget)
rem log: %TEMP%\aura_v2_batch.log  (generate progress: %TEMP%\dollgreen_DOLLGV2.txt)
rem NOTE: this file must stay pure ASCII + CRLF. %~dp0.. resolves the aura
rem       project dir, so no non-ASCII path is written here on purpose.
rem =========================================================================
set AU=%~dp0..
set PY=D:\sd-webui-aki-v4.11.1-cu128\ComfyUI_Windows_portable_cu130.7z\ComfyUI_Windows_portable\python_standalone\python.exe
set C=D:\sd-webui-aki-v4.11.1-cu128\ComfyUI_Windows_portable_cu130.7z\ComfyUI_Windows_portable
set L=%TEMP%\aura_v2_batch.log

cd /d "%C%"
echo === GEN START === > "%L%"
"%PY%" -s "tools\run_doll_green.py" IDLE PRESENT LISTENING THINKING SPEAKING SPEAKING_NEUTRAL SPEAKING_LOW PUZZLED CAMERA_LOST ERROR AWAKE ACK_NOD --len 39 --burst-len 22 --steps 8 --prefix DOLLGV2 >> "%L%" 2>&1
echo === GEN DONE === >> "%L%"

echo === INGEST START === >> "%L%"
"%PY%" -s "%AU%\tools\aura_ingest_v2.py" >> "%L%" 2>&1
echo === ALL DONE === >> "%L%"

