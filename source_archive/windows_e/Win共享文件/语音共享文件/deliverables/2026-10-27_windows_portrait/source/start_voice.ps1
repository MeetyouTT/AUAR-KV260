param([string]$VoicePython='',[switch]$WithoutPortrait)
$ErrorActionPreference='Stop'
$voiceEntry=Join-Path $PSScriptRoot 'deliverables/2026-10-18_board_dialogue/start_background_models.ps1'
& $voiceEntry -VoicePython $VoicePython
Write-Host 'Voice stack READY: ASR 8791, dialogue/TTS 8792, audio frontend 8795. Services run in background.'
if (-not $WithoutPortrait -and (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'deliverables/2026-10-27_windows_portrait/host_config.json'))) {
    & (Join-Path $PSScriptRoot 'start_portrait.ps1')
}
