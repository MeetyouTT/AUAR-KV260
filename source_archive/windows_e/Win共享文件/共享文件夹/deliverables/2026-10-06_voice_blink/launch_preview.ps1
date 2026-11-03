$ErrorActionPreference = 'Stop'
$workspaceRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$previewPython = Join-Path $workspaceRoot 'tmp\aura-validation-venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $previewPython)) { throw 'Preview Python runtime is unavailable. See the handover document.' }
Set-Location -LiteralPath $PSScriptRoot
& $previewPython -B -u (Join-Path $PSScriptRoot 'serve_preview.py') --port 8772
