param([string]$VoicePython='', [switch]$ReleaseOwnedModel)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'start_inference.ps1') -VoicePython $VoicePython -Action Stop -ReleaseOwnedModel:$ReleaseOwnedModel
