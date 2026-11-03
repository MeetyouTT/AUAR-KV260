$ErrorActionPreference='Stop'
$taskProject=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$taskPython='C:\Users\35870\.codex\visualizations\2026\10\09\01a12110-3ba4-7651-b3d7-2e6560916eb6\omnivoice-runtime-py310\Scripts\python.exe'
$taskHealth=Invoke-RestMethod -Uri 'http://192.168.50.1:8792/health' -TimeoutSec 5
if (-not $taskHealth.ready -or $taskHealth.busy -or $taskHealth.llm_model -ne 'aura-qwen3.8-27b-abliterated:iq4_xs') {throw 'Expected original model ready and idle'}
$taskProbe=@'
import json,sys
sys.path.insert(0,'deliverables/2026-10-18_board_dialogue')
from board_ssh import ssh
print(ssh('python3 -','import json,urllib.request\ns=json.load(urllib.request.urlopen("http://127.0.0.1:8783/api/state",timeout=4))\nprint(json.dumps({"phase":s["phase"],"automatic":s["automatic_conversation"],"recording":s["local_recording"]["state"],"pending":s["local_transcription"]["service"]["pending"]}))'),end='')
'@
$taskBoard=(& $taskPython -B -c $taskProbe | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or $taskBoard.phase -ne 'IDLE' -or $taskBoard.automatic.enabled -or $taskBoard.recording -eq 'RECORDING' -or $taskBoard.pending) {throw 'Board conversation must be stopped'}
$taskOwnerId=(Get-NetTCPConnection -LocalPort 8792 -State Listen | Select-Object -First 1).OwningProcess
$taskOwner=Get-CimInstance Win32_Process -Filter "ProcessId=$taskOwnerId"
if ($taskOwner.CommandLine -notlike "*$taskProject\aura\tools\board_model_host.py*" -or $taskOwner.CommandLine -notlike '*--port 8792*') {throw 'Unexpected owner of 8792'}
$taskProcesses=@(Get-CimInstance Win32_Process)
$taskDescendants=@([uint32]$taskOwnerId)
for ($taskDepth=0;$taskDepth -lt 8;$taskDepth++) {
    $taskNext=@($taskProcesses | Where-Object {$_.ParentProcessId -in $taskDescendants -and $_.ProcessId -notin $taskDescendants} | ForEach-Object {$_.ProcessId})
    if (-not $taskNext.Count) {break}
    $taskDescendants+=@($taskNext)
}
$taskVoice=@($taskProcesses | Where-Object {$_.ProcessId -in $taskDescendants -and $_.CommandLine -like '*omnivoice_voice.py*'})
@{health=$taskHealth;board=$taskBoard;host_pid=$taskOwnerId;voice_pids=@($taskVoice | ForEach-Object {$_.ProcessId});scope='PC8792 and its voice descendants only; ASR8791, Ollama11435 and board UI not restarted'} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'voice_host_reload_before.json') -Encoding UTF8
Stop-Process -Id $taskOwnerId -Force
foreach ($taskChild in $taskVoice) {Stop-Process -Id $taskChild.ProcessId -Force -ErrorAction SilentlyContinue}
& (Join-Path $taskProject 'deliverables/2026-10-18_board_dialogue/start_background_models.ps1') -VoicePython $taskPython
$taskDeadline=(Get-Date).AddSeconds(240)
do {
    try {
        $taskReady=Invoke-RestMethod -Uri 'http://192.168.50.1:8792/health' -TimeoutSec 3
        if ($taskReady.ready -and $taskReady.identity_voice_enrollment.sampling_guidance_version -eq 3 -and $taskReady.identity_features.ready -and $taskReady.identity_features.backend -eq 'WINDOWS_CPU_SFACE_ORT' -and $taskReady.identity_features.model_id -eq 'sface-2021dec-0ba9fbfa01b5') {
            $taskReady | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'voice_host_reload_ready.json') -Encoding UTF8
            $taskReady | ConvertTo-Json -Depth 7
            exit 0
        }
    } catch {}
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $taskDeadline)
throw 'Service did not become ready; inspect existing port_8792 logs'

