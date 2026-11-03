param()
$ErrorActionPreference='Stop'
$memoryProject=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$memoryRun=Join-Path $PSScriptRoot ('host-reload-'+[guid]::NewGuid().ToString('N').Substring(0,10))
New-Item -ItemType Directory -Path $memoryRun | Out-Null
$memoryHealth=Invoke-RestMethod -Uri 'http://192.168.50.1:8792/health' -TimeoutSec 4
if (-not $memoryHealth.ready -or $memoryHealth.busy) {throw 'Existing model service is not ready and idle'}
$memoryConfig=Get-Content -LiteralPath (Join-Path $memoryProject 'deliverables/2026-10-11_omnivoice_dialogue/stage_config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$memoryPython=[string]$memoryConfig.voice.python
$memoryBoardProbe=@'
import hashlib,json,subprocess,sys,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
print(ssh('python3 -B -', '''import hashlib,json,subprocess,urllib.request
get=lambda p,s:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(p)+s,timeout=4))
u=get(8783,'/api/state');c=get(8790,'/health')
unit=lambda n:hashlib.sha256(subprocess.check_output(['systemctl','cat',n])).hexdigest()
print(json.dumps({'phase':u['phase'],'playing':u['playing'],'recording':u['local_recording']['state'],
 'pending':u['local_transcription']['service']['pending'],'monitor_enabled':u['handsfree_dialogue']['enabled'],
 'ui_unit_sha256':unit('aura-avatar-ui.service'),'camera_unit_sha256':unit('aura-camera-ui.service'),
 'camera_pid':c['pid'],'camera_epoch':c['service_epoch']}))
''',timeout=15),end='')
'@
$memoryBoard=(& $memoryPython -B -c $memoryBoardProbe $memoryProject | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or $memoryBoard.phase -ne 'IDLE' -or $memoryBoard.playing -or $memoryBoard.recording -eq 'RECORDING' -or $memoryBoard.pending) {throw 'Board is not confirmed idle; no restart'}
if ($memoryBoard.monitor_enabled) {throw 'Monitoring must already be paused for this coordinated reload; no preference change performed'}
$memoryOwnerId=(Get-NetTCPConnection -LocalPort 8792 -State Listen | Select-Object -First 1).OwningProcess
$memoryOwner=Get-CimInstance Win32_Process -Filter "ProcessId=$memoryOwnerId"
$memoryExpected=Join-Path $memoryProject 'aura/tools/board_model_host.py'
if ($memoryOwner.CommandLine -notlike '*board_model_host.py*' -or $memoryOwner.CommandLine -notlike '*--port 8792*' -or -not $memoryOwner.CommandLine.Contains($memoryExpected)) {throw 'Unrecognized model service owner; no restart'}
$memoryChildren=@(Get-CimInstance Win32_Process -Filter "ParentProcessId=$memoryOwnerId" | Where-Object {$_.CommandLine -like '*omnivoice_voice.py*'})
[pscustomobject]@{health_before=$memoryHealth;board_before=$memoryBoard;old_host_pid=$memoryOwnerId;scope='PC 8792 only; no board service or monitoring changes'} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $memoryRun 'before.json') -Encoding UTF8
Stop-Process -Id $memoryOwnerId -Force
foreach($memoryChild in $memoryChildren){Stop-Process -Id $memoryChild.ProcessId -Force -ErrorAction SilentlyContinue}
$memoryBackup=@'
import json,sqlite3,sys,uuid
from pathlib import Path
root=Path(sys.argv[1])/'deliverables/2026-10-18_board_dialogue/model_host'
src=root/'conversations.sqlite3';folder=root/'backups';folder.mkdir(exist_ok=True)
dst=folder/('conversations-pre-memory-controls-'+uuid.uuid4().hex[:10]+'.sqlite3')
with sqlite3.connect(src) as a,sqlite3.connect(dst) as b:a.backup(b)
print(json.dumps({'database_backup':str(dst),'user_rows_exported':False}))
'@
try {
    & $memoryPython -B -c $memoryBackup $memoryProject | Set-Content -LiteralPath (Join-Path $memoryRun 'database_backup.json') -Encoding UTF8
    if ($LASTEXITCODE -ne 0) {throw 'Database backup failed'}
} catch {
    & (Join-Path $memoryProject 'deliverables/2026-10-18_board_dialogue/start_background_models.ps1') -VoicePython $memoryPython
    throw
}
& (Join-Path $memoryProject 'deliverables/2026-10-18_board_dialogue/start_background_models.ps1') -VoicePython $memoryPython
$memoryUntil=[DateTime]::UtcNow.AddSeconds(180)
do {
    try {
        $memoryAfter=Invoke-RestMethod -Uri 'http://192.168.50.1:8792/health' -TimeoutSec 4
        if ($memoryAfter.ready -and $memoryAfter.conversation_memory.memory_controls -eq 'explicit_conversation_facts_v1') {break}
    } catch {}
    Start-Sleep -Seconds 2
} while ([DateTime]::UtcNow -lt $memoryUntil)
if (-not $memoryAfter.ready -or $memoryAfter.conversation_memory.memory_controls -ne 'explicit_conversation_facts_v1') {throw 'Updated model service readiness not confirmed; preserve migrated database and inspect logs'}
$memoryBoardAfter=(& $memoryPython -B -c $memoryBoardProbe $memoryProject | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0) {throw 'Cannot confirm unchanged board after reload'}
foreach($memoryField in @('ui_unit_sha256','camera_unit_sha256','camera_pid','camera_epoch','monitor_enabled')) {
    if ($memoryBoard.$memoryField -ne $memoryBoardAfter.$memoryField) {throw "Board changed during reload: $memoryField"}
}
if ($memoryAfter.llm_model -ne $memoryHealth.llm_model -or $memoryAfter.asr_model -ne $memoryHealth.asr_model -or $memoryAfter.tts -ne $memoryHealth.tts -or $memoryAfter.num_step -ne $memoryHealth.num_step) {throw 'Model configuration unexpectedly changed'}
[pscustomobject]@{status='PC_MEMORY_CONTROLS_READY';health=$memoryAfter;board_after=$memoryBoardAfter;board_unchanged=$true;human_memory_trial_verified=$false;human_barge_in_verified=$false} | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath (Join-Path $memoryRun 'after.json') -Encoding UTF8
[pscustomobject]@{status='PC_MEMORY_CONTROLS_READY';evidence=$memoryRun;board_unchanged=$true;monitor_enabled=$memoryBoardAfter.monitor_enabled} | ConvertTo-Json
