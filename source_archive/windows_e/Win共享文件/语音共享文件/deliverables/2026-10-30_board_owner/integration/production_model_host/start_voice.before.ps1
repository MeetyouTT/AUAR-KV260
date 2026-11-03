param([string]$VoicePython='',[switch]$WithoutPortrait)
$ErrorActionPreference='Stop'
$deviceEntry=Join-Path $PSScriptRoot 'deliverables/2026-10-28_device_skills/start_devices.ps1'
if (Test-Path -LiteralPath $deviceEntry) { & $deviceEntry }
$voiceEntry=Join-Path $PSScriptRoot 'deliverables/2026-10-18_board_dialogue/start_background_models.ps1'
& $voiceEntry -VoicePython $VoicePython
Write-Host 'Voice stack READY: ASR 8791, dialogue/TTS 8792, audio frontend 8795. Services run in background.'
if (-not $WithoutPortrait -and (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'aura/config/portrait_host.local.json'))) {
    & (Join-Path $PSScriptRoot 'start_portrait.ps1')
}
