param([string]$VoicePython = '')
$ErrorActionPreference = 'Stop'
$AuraRoot = Split-Path -Parent $PSScriptRoot
$SharedRoot = Split-Path -Parent $AuraRoot
if (-not $VoicePython) {
    foreach ($name in @('machine_config.json', 'stage_config.json')) {
        $configPath = Join-Path $SharedRoot ('deliverables/2026-10-11_omnivoice_dialogue/' + $name)
        if (Test-Path -LiteralPath $configPath -PathType Leaf) {
            $config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $candidate = [string]$config.microphone.python
            if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
                $VoicePython = $candidate
                break
            }
        }
    }
}
if (-not $VoicePython -or -not (Test-Path -LiteralPath $VoicePython -PathType Leaf)) {
    throw 'Specify the accepted voice environment: .\scripts\start_board_asr.ps1 -VoicePython C:\path\to\python.exe'
}
& $VoicePython -c 'import sherpa_onnx, numpy'
if ($LASTEXITCODE -ne 0) { throw 'The selected Python needs the accepted sherpa-onnx / numpy environment.' }
Write-Host 'Starting actual Paraformer on port 8791. Wait for READY; keep this window open.'
& $VoicePython -B (Join-Path $AuraRoot 'tools/asr_server.py') --listen 0.0.0.0 --port 8791
if ($LASTEXITCODE -ne 0) { throw 'ASR service exited with an error; see the output above.' }
