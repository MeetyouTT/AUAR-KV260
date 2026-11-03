param([switch]$WaitForDownload,[switch]$WaitForReady,[ValidateSet('probe_dflash.py','memory_schedule_probe.py','trim_cache_probe.py','cuda_graph_probe.py','graph_validation.py')][string]$ProbeScript='probe_dflash.py')
$ErrorActionPreference='Stop'
$trialWaitStarted=Get-Date
while (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'draft_download.json'))) {
    if (-not $WaitForDownload -or ((Get-Date)-$trialWaitStarted).TotalSeconds -gt 600) {throw 'Verified draft manifest unavailable; no service changes performed'}
    Start-Sleep -Seconds 2
}
$trialProject=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$trialConfig=Get-Content -LiteralPath (Join-Path $trialProject 'deliverables/2026-10-11_omnivoice_dialogue/stage_config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$trialPython=[string]$trialConfig.voice.python
$trialReadyStarted=Get-Date
do {
    try {$trialHealth=Invoke-RestMethod -Uri 'http://192.168.50.1:8792/health' -TimeoutSec 5; break}
    catch {if (-not $WaitForReady -or ((Get-Date)-$trialReadyStarted).TotalSeconds -gt 300) {throw}; Start-Sleep -Seconds 2}
} while ($true)
if (-not $trialHealth.ready -or $trialHealth.busy -or $trialHealth.llm_model -ne 'aura-qwen3.8-27b-abliterated:iq4_xs') {throw 'Original service not confirmed ready/idle/27B'}
$trialProbe=@'
import json,sys
sys.path.insert(0,'deliverables/2026-10-18_board_dialogue')
from board_ssh import ssh
print(ssh('python3 -','import json,urllib.request\ns=json.load(urllib.request.urlopen("http://127.0.0.1:8783/api/state",timeout=4))\nprint(json.dumps({"phase":s.get("phase"),"playing":s.get("playing"),"recording":s.get("local_recording",{}).get("state"),"pending":s.get("local_transcription",{}).get("service",{}).get("pending")}))'),end='')
'@
$trialBoard=(& $trialPython -B -c $trialProbe | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or $trialBoard.phase -ne 'IDLE' -or $trialBoard.playing -or $trialBoard.recording -eq 'RECORDING' -or $trialBoard.pending) {throw 'Board not confirmed idle'}
$trialOwnerId=(Get-NetTCPConnection -LocalPort 8792 -State Listen | Select-Object -First 1).OwningProcess
$trialOwner=Get-CimInstance Win32_Process -Filter "ProcessId=$trialOwnerId"
if ($trialOwner.CommandLine -notlike '*board_model_host.py*' -or $trialOwner.CommandLine -notlike '*--port 8792*' -or $trialOwner.CommandLine -notlike '*E:\Win共享文件\语音共享文件\*') {throw 'Unknown host owner'}
$trialAll=@(Get-CimInstance Win32_Process)
$trialDescendants=@([uint32]$trialOwnerId)
for ($trialDepth=0; $trialDepth -lt 8; $trialDepth++) {
    $trialNext=@($trialAll | Where-Object {$_.ParentProcessId -in $trialDescendants -and $_.ProcessId -notin $trialDescendants} | ForEach-Object {$_.ProcessId})
    if (-not $trialNext.Count) {break}
    $trialDescendants+=@($trialNext)
}
$trialChildren=@($trialAll | Where-Object {$_.ProcessId -in $trialDescendants -and $_.CommandLine -like '*omnivoice_voice.py*'})
$trialTarget='D:\AIModels\Ollama-AURA\blobs\sha256-d83adbbbaace8acdfcfe28004f779326176b9df00b4ec99dc6c24d749723d3b9'
$trialHash=(Get-FileHash -LiteralPath $trialTarget -Algorithm SHA256).Hash.ToLowerInvariant()
if ($trialHash -ne 'd83adbbbaace8acdfcfe28004f779326176b9df00b4ec99dc6c24d749723d3b9') {throw 'Original target hash differs'}
$trialShow=Invoke-RestMethod -Uri 'http://127.0.0.1:11435/api/show' -Method Post -ContentType 'application/json' -Body '{"model":"aura-qwen3.8-27b-abliterated:iq4_xs"}' -TimeoutSec 8
[System.IO.File]::WriteAllText((Join-Path $PSScriptRoot 'original_template.txt'),[string]$trialShow.template,[System.Text.UTF8Encoding]::new($false))
@{health=$trialHealth;board=$trialBoard;host_pid=$trialOwnerId;voice_pids=@($trialChildren | ForEach-Object {$_.ProcessId});target_sha256=$trialHash;scope='temporary PC8792+its TTS descendants and unload of project 27B only; no board/ASR/vision changes'} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'before.json') -Encoding UTF8
try {
    Stop-Process -Id $trialOwnerId -Force
    foreach ($trialChild in $trialChildren) {Stop-Process -Id $trialChild.ProcessId -Force -ErrorAction SilentlyContinue}
    Invoke-RestMethod -Uri 'http://127.0.0.1:11435/api/generate' -Method Post -ContentType 'application/json' -Body '{"model":"aura-qwen3.8-27b-abliterated:iq4_xs","keep_alive":0}' -TimeoutSec 20 | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'unload.json') -Encoding UTF8
    & $trialPython -B -u (Join-Path $PSScriptRoot $ProbeScript)
    if ($LASTEXITCODE -ne 0) {throw 'Candidate probe failed; inspect probe.json and runner logs'}
} finally {
    & (Join-Path $trialProject 'deliverables/2026-10-18_board_dialogue/start_background_models.ps1') -VoicePython $trialPython
}
