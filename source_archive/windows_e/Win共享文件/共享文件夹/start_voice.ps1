param([string]$VoicePython='')
$ErrorActionPreference='Stop'
$voiceEntry=Join-Path $PSScriptRoot 'deliverables/2026-10-18_board_dialogue/start_background_models.ps1'
& $voiceEntry -VoicePython $VoicePython
Write-Host 'Models start in background; wait for actual READY in the service logs. Existing compatible listeners are reused.'
