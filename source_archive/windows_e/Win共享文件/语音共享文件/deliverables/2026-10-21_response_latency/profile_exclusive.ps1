$ErrorActionPreference='Stop'
$latencyProject=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$latencyConfig=Get-Content -LiteralPath (Join-Path $latencyProject 'deliverables/2026-10-11_omnivoice_dialogue/stage_config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$latencyPython=[string]$latencyConfig.voice.python
$latencyHealth=Invoke-RestMethod -Uri 'http://192.168.50.1:8792/health' -TimeoutSec 4
if (-not $latencyHealth.ready -or $latencyHealth.busy) {throw 'PC voice host not ready and idle'}
$latencyProbe=@'
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
print(ssh('python3 -B -', '''import json,urllib.request
u=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
print(json.dumps({'phase':u['phase'],'playing':u['playing'],'enabled':u['handsfree_dialogue']['enabled'],'recording':u['local_recording']['state'],'pending':u['local_transcription']['service']['pending']}))''',timeout=12),end='')
'@
$latencyBoard=(& $latencyPython -B -c $latencyProbe $latencyProject | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or $latencyBoard.enabled -or $latencyBoard.phase -ne 'IDLE' -or $latencyBoard.playing -or $latencyBoard.recording -eq 'RECORDING' -or $latencyBoard.pending) {throw 'Board must already be paused and idle; no stop performed'}
$latencyOwnerId=(Get-NetTCPConnection -LocalPort 8792 -State Listen | Select-Object -First 1).OwningProcess
$latencyProcesses=@(Get-CimInstance Win32_Process)
$latencyOwner=$latencyProcesses | Where-Object {$_.ProcessId -eq $latencyOwnerId}
$latencyExpected=Join-Path $latencyProject 'aura/tools/board_model_host.py'
if (-not $latencyOwner.CommandLine.Contains($latencyExpected) -or $latencyOwner.CommandLine -notlike '*--port 8792*') {throw 'Unexpected PC8792 owner'}
$latencyDescendants=@()
$latencyParents=@($latencyOwnerId)
while ($latencyParents.Count -gt 0) {
    $latencyChildren=@($latencyProcesses | Where-Object {$_.ParentProcessId -in $latencyParents})
    $latencyDescendants+=$latencyChildren
    $latencyParents=@($latencyChildren | ForEach-Object {$_.ProcessId})
}
$latencyVoice=@($latencyDescendants | Where-Object {$_.CommandLine -like '*omnivoice_voice.py*'})
[pscustomobject]@{health=$latencyHealth;board=$latencyBoard;host_pid=$latencyOwnerId;tts_pids=@($latencyVoice | ForEach-Object {$_.ProcessId});scope='Only PC8792 and its verified TTS descendants; preserve board/current preference/Ollama/ASR'} | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'profile_before.json') -Encoding UTF8
Stop-Process -Id $latencyOwnerId -Force
foreach($latencyChild in $latencyVoice){Stop-Process -Id $latencyChild.ProcessId -Force -ErrorAction SilentlyContinue}
try {
    $env:PYTHONIOENCODING='utf-8'
    & $latencyPython -B (Join-Path $PSScriptRoot 'profile_pipeline.py') --multi
    if ($LASTEXITCODE -ne 0) {throw 'Latency comparison failed; original service will be restored'}
} finally {
    & (Join-Path $latencyProject 'deliverables/2026-10-18_board_dialogue/start_background_models.ps1') -VoicePython $latencyPython
}
