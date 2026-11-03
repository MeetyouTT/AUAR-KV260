$ErrorActionPreference='Stop'
$latencyProject=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$latencyConfig=Get-Content -LiteralPath (Join-Path $latencyProject 'deliverables/2026-10-11_omnivoice_dialogue/stage_config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$latencyPython=[string]$latencyConfig.voice.python
$latencyProfile=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'latest_profile.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not ($latencyProfile.summary | Where-Object {$_.same_reply -and $_.improvement_ms -ge 1000 -and $_.max_estimated_second_segment_late_ms -eq 0})) {throw 'No verified meaningful lead-sentence gain'}
$latencyBefore=Invoke-RestMethod -Uri 'http://192.168.50.1:8792/health' -TimeoutSec 4
if (-not $latencyBefore.ready -or $latencyBefore.busy) {throw 'Original model host not confirmed ready and idle'}
$latencyProbe=@'
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
print(ssh('python3 -B -', '''import hashlib,json,subprocess,urllib.request
u=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
c=json.load(urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=4))
unit=lambda n:hashlib.sha256(subprocess.check_output(['systemctl','cat',n])).hexdigest()
print(json.dumps({'phase':u['phase'],'playing':u['playing'],'enabled':u['handsfree_dialogue']['enabled'],'recording':u['local_recording']['state'],'pending':u['local_transcription']['service']['pending'],'ui_unit_sha256':unit('aura-avatar-ui.service'),'camera_unit_sha256':unit('aura-camera-ui.service'),'camera_pid':c['pid'],'camera_epoch':c['service_epoch'],'barge_in':u['voice_barge_in']['enabled'],'early_listen':u['handsfree_dialogue']['listening_timing']['enabled']}))''',timeout=12),end='')
'@
$latencyBoard=(& $latencyPython -B -c $latencyProbe $latencyProject | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or $latencyBoard.enabled -or $latencyBoard.phase -ne 'IDLE' -or $latencyBoard.playing -or $latencyBoard.recording -eq 'RECORDING' -or $latencyBoard.pending) {throw 'Board not already paused and idle'}
$latencyOptionsPath=Join-Path $latencyProject 'aura/config/voice_latency.json'
$latencyOptionsBefore=Get-Content -LiteralPath $latencyOptionsPath -Raw -Encoding UTF8
$latencyExpected=Join-Path $latencyProject 'aura/tools/board_model_host.py'
function Stop-LatencyOwnedHost {
    $latencyAll=@(Get-CimInstance Win32_Process)
    $latencyOwners=@($latencyAll | Where-Object {$_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -and $_.CommandLine.Contains($latencyExpected) -and $_.CommandLine -like '*--port 8792*'})
    if ($latencyOwners.Count -eq 0) {return}
    $latencyParents=@($latencyOwners | ForEach-Object {$_.ProcessId})
    $latencyDesc=@()
    while ($latencyParents.Count -gt 0) {
        $latencyNext=@($latencyAll | Where-Object {$_.ParentProcessId -in $latencyParents -and $_.ProcessId -notin @($latencyDesc | ForEach-Object {$_.ProcessId})})
        $latencyDesc+=$latencyNext
        $latencyParents=@($latencyNext | ForEach-Object {$_.ProcessId})
    }
    foreach($latencyProcess in @($latencyDesc | Where-Object {$_.CommandLine -like '*omnivoice_voice.py*'})) {Stop-Process -Id $latencyProcess.ProcessId -Force -ErrorAction SilentlyContinue}
    foreach($latencyProcess in $latencyOwners) {Stop-Process -Id $latencyProcess.ProcessId -Force -ErrorAction SilentlyContinue}
}
[pscustomobject]@{health=$latencyBefore;board=$latencyBoard} | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'deployment_before.json') -Encoding UTF8
try {
    $latencyOwnerId=(Get-NetTCPConnection -LocalPort 8792 -State Listen | Select-Object -First 1).OwningProcess
    $latencyOwner=Get-CimInstance Win32_Process -Filter "ProcessId=$latencyOwnerId"
    if (-not $latencyOwner.CommandLine.Contains($latencyExpected)) {throw 'Unknown service owner'}
    Stop-LatencyOwnedHost
    $latencyOptions=$latencyOptionsBefore | ConvertFrom-Json
    $latencyOptions | Add-Member -NotePropertyName first_sentence_chat -NotePropertyValue $true -Force
    $latencyOptions | ConvertTo-Json | Set-Content -LiteralPath $latencyOptionsPath -Encoding UTF8
    & (Join-Path $latencyProject 'deliverables/2026-10-18_board_dialogue/start_background_models.ps1') -VoicePython $latencyPython
    $latencyDeadline=[DateTime]::UtcNow.AddSeconds(180)
    $latencyAfter=$null
    do {
        try {
            $latencyAfter=Invoke-RestMethod -Uri 'http://192.168.50.1:8792/health' -TimeoutSec 3
            if ($latencyAfter.ready -and $latencyAfter.latency_options.first_sentence_chat) {break}
        } catch {}
        Start-Sleep -Seconds 2
    } while ([DateTime]::UtcNow -lt $latencyDeadline)
    if (-not $latencyAfter.ready -or -not $latencyAfter.latency_options.first_sentence_chat) {throw 'New model host not ready'}
    foreach($latencyField in @('llm_model','asr_model','tts','num_step')) {if ($latencyBefore.$latencyField -ne $latencyAfter.$latencyField) {throw "Model configuration changed: $latencyField"}}
    if ($latencyAfter.conversation_memory.memory_controls -ne 'explicit_conversation_facts_v1') {throw 'Memory controls unavailable'}
    $latencyBoardAfter=(& $latencyPython -B -c $latencyProbe $latencyProject | ConvertFrom-Json)
    if ($LASTEXITCODE -ne 0) {throw 'Board verification failed'}
    foreach($latencyField in @('ui_unit_sha256','camera_unit_sha256','camera_pid','camera_epoch','enabled','barge_in','early_listen')) {if ($latencyBoard.$latencyField -ne $latencyBoardAfter.$latencyField) {throw "Board state changed: $latencyField"}}
    [pscustomobject]@{status='PC_FIRST_SENTENCE_READY';health=$latencyAfter;board=$latencyBoardAfter;human_latency_verified=$false;scope='Only PC8792 reload; UI/camera/preferences unchanged'} | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'deployment.json') -Encoding UTF8
    Write-Output 'PC_FIRST_SENTENCE_READY'
} catch {
    Stop-LatencyOwnedHost
    $latencyOptionsBefore | Set-Content -LiteralPath $latencyOptionsPath -Encoding UTF8
    & (Join-Path $latencyProject 'deliverables/2026-10-18_board_dialogue/start_background_models.ps1') -VoicePython $latencyPython
    [pscustomobject]@{status='FLAG_RESTORED_AFTER_FAILURE';error=$_.Exception.Message;readiness_not_yet_verified=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'deployment.json') -Encoding UTF8
    throw
}
