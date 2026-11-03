@echo off
cd /d "%~dp0"
python serve_preview.py --port 8769
pause
