$ErrorActionPreference='Stop'
$streamEvidence=if($env:AURA_TTS_TRIAL_DIR){$env:AURA_TTS_TRIAL_DIR}else{$PSScriptRoot}
New-Item -ItemType Directory -Path $streamEvidence -Force | Out-Null
$streamProject=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$streamConfig=Get-Content -LiteralPath (Join-Path $streamProject 'deliverables/2026-10-11_omnivoice_dialogue/stage_config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$streamPython=[string]$streamConfig.voice.python
$streamDownload=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'download.json') -Raw | ConvertFrom-Json
if ($streamDownload.status -ne 'VERIFIED') {throw 'Candidate files not verified; no service changes'}
$streamHealth=Invoke-RestMethod -Uri 'http://192.168.50.1:8792/health' -TimeoutSec 6
if (-not $streamHealth.ready -or $streamHealth.busy -or $streamHealth.llm_model -ne 'aura-qwen3.8-27b-abliterated:iq4_xs') {throw 'Original service not confirmed ready/idle/27B'}
$streamBoardCode=@'
import json,sys
sys.path.insert(0,'deliverables/2026-10-18_board_dialogue')
from board_ssh import ssh
print(ssh('python3 -','import json,urllib.request,pathlib\ns=json.load(urllib.request.urlopen("http://127.0.0.1:8783/api/state",timeout=4))\ncamera=json.load(urllib.request.urlopen("http://127.0.0.1:8790/health",timeout=4))\nprint(json.dumps({"phase":s.get("phase"),"playing":s.get("playing"),"recording":s.get("local_recording",{}).get("state"),"pending":s.get("local_transcription",{}).get("service",{}).get("pending"),"camera":camera,"boot_id":pathlib.Path("/proc/sys/kernel/random/boot_id").read_text().strip()}))'),end='')
'@
$streamBoard=(& $streamPython -B -c $streamBoardCode | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or $streamBoard.phase -ne 'IDLE' -or $streamBoard.playing -or $streamBoard.recording -eq 'RECORDING' -or $streamBoard.pending) {throw 'Board not confirmed idle'}
if (Get-NetTCPConnection -LocalPort 51889 -State Listen -ErrorAction SilentlyContinue) {throw 'Candidate port already in use'}
$streamOwnerId=(Get-NetTCPConnection -LocalPort 8792 -State Listen | Select-Object -First 1).OwningProcess
$streamOwner=Get-CimInstance Win32_Process -Filter "ProcessId=$streamOwnerId"
if ($streamOwner.CommandLine -notlike '*board_model_host.py*' -or $streamOwner.CommandLine -notlike '*--port 8792*' -or $streamOwner.CommandLine -notlike '*E:\Win共享文件\语音共享文件\*') {throw 'Unknown host owner'}
$streamAll=@(Get-CimInstance Win32_Process)
$streamDescendants=@([uint32]$streamOwnerId)
for ($streamDepth=0; $streamDepth -lt 8; $streamDepth++) {
    $streamNext=@($streamAll | Where-Object {$_.ParentProcessId -in $streamDescendants -and $_.ProcessId -notin $streamDescendants} | ForEach-Object {$_.ProcessId})
    if (-not $streamNext.Count) {break}
    $streamDescendants+=@($streamNext)
}
$streamChildren=@($streamAll | Where-Object {$_.ProcessId -in $streamDescendants -and $_.CommandLine -like '*omnivoice_voice.py*'})
@{health=$streamHealth;board=$streamBoard;host_pid=$streamOwnerId;voice_pids=@($streamChildren | ForEach-Object {$_.ProcessId});scope='Temporary PC host/TTS only; original 27B/Ollama/ASR/board services retained'} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $streamEvidence 'services_before.json') -Encoding UTF8
try {
    Stop-Process -Id $streamOwnerId -Force
    foreach ($streamChild in $streamChildren) {Stop-Process -Id $streamChild.ProcessId -Force -ErrorAction SilentlyContinue}
    $streamScript=if($env:AURA_TTS_CONTROLLER -eq 'run_cli_matrix.py'){'run_cli_matrix.py'}else{'run_candidate.py'}
    & $streamPython -B -u (Join-Path $PSScriptRoot $streamScript)
    if ($LASTEXITCODE -ne 0) {throw 'Streaming candidate failed; logs retained'}
} finally {
    & (Join-Path $streamProject 'deliverables/2026-10-18_board_dialogue/start_background_models.ps1') -VoicePython $streamPython
}
