$ErrorActionPreference = 'Stop'
$taskProject = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$taskPython = (Get-Content -LiteralPath (Join-Path $taskProject 'deliverables/2026-10-11_omnivoice_dialogue/stage_config.json') -Raw | ConvertFrom-Json).voice.python
& $taskPython -B (Join-Path $PSScriptRoot 'start_frontend.py')
if ($LASTEXITCODE -ne 0) { throw 'Frontend start failed; inspect frontend_stderr.log' }
