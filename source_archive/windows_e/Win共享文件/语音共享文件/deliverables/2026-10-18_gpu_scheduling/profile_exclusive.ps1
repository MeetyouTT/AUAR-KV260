param([ValidateSet('profile_pipeline.py','profile_grammar_pipeline.py','profile_integrated.py')][string]$Profile='profile_pipeline.py')
$ErrorActionPreference='Stop'
$schedulingProject=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$schedulingHealth=Invoke-RestMethod -Uri 'http://192.168.50.1:8792/health' -TimeoutSec 4
if ($schedulingHealth.busy) {throw 'Host is busy; no stop performed'}
$schedulingConfig=Get-Content -LiteralPath (Join-Path $schedulingProject 'deliverables/2026-10-11_omnivoice_dialogue/stage_config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$schedulingPython=[string]$schedulingConfig.voice.python
$schedulingProbe=@'
import json,sys
sys.path.insert(0,'deliverables/2026-10-18_board_dialogue')
from board_ssh import ssh
print(ssh('python3 -','import json,urllib.request\ns=json.load(urllib.request.urlopen("http://127.0.0.1:8783/api/state",timeout=4))\nprint(json.dumps({"phase":s.get("phase"),"playing":s.get("playing"),"recording":s.get("local_recording",{}).get("state"),"pending":s.get("local_transcription",{}).get("service",{}).get("pending")}))'),end='')
'@
$schedulingBoard=(& $schedulingPython -B -c $schedulingProbe | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or $schedulingBoard.phase -ne 'IDLE' -or $schedulingBoard.playing -or $schedulingBoard.recording -eq 'RECORDING' -or $schedulingBoard.pending) {throw 'Board not confirmed idle; no stop performed'}
$schedulingOwnerId=(Get-NetTCPConnection -LocalPort 8792 -State Listen | Select-Object -First 1).OwningProcess
$schedulingOwner=Get-CimInstance Win32_Process -Filter "ProcessId=$schedulingOwnerId"
if ($schedulingOwner.CommandLine -notlike '*board_model_host.py*' -or $schedulingOwner.CommandLine -notlike '*--port 8792*') {throw 'Unknown host process; no stop performed'}
$schedulingChildren=@(Get-CimInstance Win32_Process -Filter "ParentProcessId=$schedulingOwnerId" | Where-Object {$_.CommandLine -like '*omnivoice_voice.py*'})
$schedulingSnapshot=if ($Profile -eq 'profile_pipeline.py') {'exclusive_before.json'} elseif ($Profile -eq 'profile_grammar_pipeline.py') {'grammar_exclusive_before.json'} else {'integrated_exclusive_before.json'}
[pscustomobject]@{health_before=$schedulingHealth;board_before=$schedulingBoard;host_pid=$schedulingOwnerId;voice_pids=@($schedulingChildren | ForEach-Object {$_.ProcessId});scope='PC8792+its voice child only; board, ASR and Ollama remain'} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot $schedulingSnapshot) -Encoding UTF8
Stop-Process -Id $schedulingOwnerId -Force
foreach ($schedulingChild in $schedulingChildren) {Stop-Process -Id $schedulingChild.ProcessId -Force -ErrorAction SilentlyContinue}
try {
    & $schedulingPython -B (Join-Path $PSScriptRoot $Profile)
    if ($LASTEXITCODE -ne 0) {throw 'Exclusive benchmark failed; inspect saved evidence'}
} finally {
    & (Join-Path $schedulingProject 'deliverables/2026-10-18_board_dialogue/start_background_models.ps1') -VoicePython $schedulingPython
}
