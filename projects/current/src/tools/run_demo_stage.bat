@echo off
setlocal
set "STAGE_ROOT=%~dp0..\..\deliverables\2026-10-06_xilan_live"
call "%STAGE_ROOT%\run_live_stage.bat" %*
endlocal
