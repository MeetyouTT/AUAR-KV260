$ErrorActionPreference='Stop'
$conversationProject=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$conversationHealth=Invoke-RestMethod 'http://192.168.50.1:8792/health' -TimeoutSec 4
if ($conversationHealth.busy) {throw 'Finish the current turn before rollback'}
# Run rollback.py first to restore the previous board UI. Keep databases intact.
foreach ($conversationName in @('board_model_host.py','voice_channel_source.py','dialogue_host_ollama.py')) {
    $conversationBackup=Join-Path $PSScriptRoot ('before/aura/tools/'+$conversationName)
    if (-not (Test-Path -LiteralPath $conversationBackup -PathType Leaf)) {throw 'Missing source backup'}
}
foreach ($conversationName in @('board_model_host.py','voice_channel_source.py','dialogue_host_ollama.py')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot ('before/aura/tools/'+$conversationName)) -Destination (Join-Path $conversationProject ('aura/tools/'+$conversationName))
}
& (Join-Path $PSScriptRoot 'restart_host.ps1')
