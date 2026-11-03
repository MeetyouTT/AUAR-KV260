param([string]$VoicePython='', [switch]$WithoutPortrait)
$ErrorActionPreference='Stop'
# Compatibility parameters remain accepted. Windows now owns model execution
# only; device/ASR/memory/identity/playback and portraits belong to the board.
& (Join-Path $PSScriptRoot 'start_inference.ps1') -VoicePython $VoicePython
