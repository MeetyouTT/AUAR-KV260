param()
$ErrorActionPreference='Stop'
$channelProject=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$channelHealth=Invoke-RestMethod -Uri 'http://192.168.50.1:8792/health' -TimeoutSec 4
if ($channelHealth.busy) {throw 'Existing model service is busy; no restart performed'}
$channelConfig=Get-Content -LiteralPath (Join-Path $channelProject 'deliverables/2026-10-11_omnivoice_dialogue/stage_config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$channelPython=[string]$channelConfig.voice.python
$channelProbe=@'
import json,sys
sys.path.insert(0,'deliverables/2026-10-18_board_dialogue')
from board_ssh import ssh
print(ssh('python3 -', 'import json,urllib.request\nu=json.load(urllib.request.urlopen("http://127.0.0.1:8783/api/state",timeout=4))\nprint(json.dumps({"phase":u.get("phase"),"playing":u.get("playing"),"recording":u.get("local_recording",{}).get("state"),"pending":u.get("local_transcription",{}).get("service",{}).get("pending")}))'),end='')
'@
$channelBoard=(& $channelPython -B -c $channelProbe | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or $channelBoard.phase -ne 'IDLE' -or $channelBoard.playing -or $channelBoard.recording -eq 'RECORDING' -or $channelBoard.pending) {throw 'Board is not confirmed idle; no restart performed'}
$channelOwnerId=(Get-NetTCPConnection -LocalPort 8792 -State Listen | Select-Object -First 1).OwningProcess
$channelOwner=Get-CimInstance Win32_Process -Filter "ProcessId=$channelOwnerId"
if ($channelOwner.CommandLine -notlike '*board_model_host.py*' -or $channelOwner.CommandLine -notlike '*--port 8792*') {throw 'Unrecognized listener; no restart performed'}
$channelChildren=@(Get-CimInstance Win32_Process -Filter "ParentProcessId=$channelOwnerId" | Where-Object {$_.CommandLine -like '*omnivoice_voice.py*'})
[pscustomobject]@{health_before=$channelHealth;board_before=$channelBoard;old_host_pid=$channelOwnerId;old_voice_pids=@($channelChildren | ForEach-Object {$_.ProcessId});scope='PC model service only; board UI, DPU and FPGA unchanged'} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'restart_before.json') -Encoding UTF8
Stop-Process -Id $channelOwnerId -Force
foreach ($channelChild in $channelChildren) {Stop-Process -Id $channelChild.ProcessId -Force -ErrorAction SilentlyContinue}
& (Join-Path $channelProject 'deliverables/2026-10-18_board_dialogue/start_background_models.ps1') -VoicePython $channelPython
