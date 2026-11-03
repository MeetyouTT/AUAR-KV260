param([switch]$Rollback)
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$auraRoot='E:\Win共享文件\语音共享文件\aura'
$configPath=Join-Path $auraRoot 'config\voice_latency.json'
$health=Invoke-RestMethod 'http://192.168.50.1:8792/health' -TimeoutSec 5
if (-not $health.ready -or $health.busy -or $health.dependencies.tts.request_active -or $health.service_revision -ne 'voice-timeline-20261028-r2') {throw 'Service not idle/current'}
$board=Get-Content (Join-Path $taskRoot 'before.json') -Raw | ConvertFrom-Json
if (-not $board.board.preflight_ready) {throw 'Board not idle'}
$all=Get-CimInstance Win32_Process
$listener=Get-NetTCPConnection -State Listen -LocalPort 8792
$owner=$all | Where-Object ProcessId -eq $listener.OwningProcess
if (-not $owner.CommandLine.Contains('2026-10-28_timeline_summaries\diagnostic_voice_entry.py')) {throw 'Unknown owner'}
$parent=$all | Where-Object ProcessId -eq $owner.ParentProcessId
if (-not $parent.CommandLine.Contains('diagnostic_voice_entry.py')) {throw 'Unknown parent'}
$workers=@($all | Where-Object {$_.ParentProcessId -eq $owner.ProcessId -and $_.Name -eq 'python.exe'})
if ($workers.Count -ne 1 -or -not $workers[0].CommandLine.Contains('omnivoice_voice.py')) {throw 'Unknown TTS owner'}
$beforeText=[IO.File]::ReadAllText($configPath)
$cfg=$beforeText | ConvertFrom-Json
$backup=Join-Path $taskRoot 'voice_latency.before.json'
if (-not $Rollback) {
 if (-not $cfg.compact_grammar) {throw 'Already false; investigate'}
 if (Test-Path $backup) {throw 'Backup already exists'}
 Copy-Item -LiteralPath $configPath -Destination $backup
 $newText=$beforeText -replace '"compact_grammar"\s*:\s*true','"compact_grammar": false'
 [IO.File]::WriteAllText($configPath,$newText,[Text.UTF8Encoding]::new($false))
} else {Copy-Item -LiteralPath $backup -Destination $configPath -Force}
$evidence=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');rollback=[bool]$Rollback;command=$parent.CommandLine;owner=$owner.ProcessId;parent=$parent.ProcessId;workers=@($workers.ProcessId);health_before=$health;config_hash=(Get-FileHash $configPath).Hash;other_listeners=@(Get-NetTCPConnection -State Listen | Where-Object LocalPort -in @(8791,8795,8796,11435) | Select-Object LocalPort,OwningProcess)}
foreach ($worker in $workers) {Stop-Process -Id $worker.ProcessId -Force}
Stop-Process -Id $owner.ProcessId -Force
Stop-Process -Id $parent.ProcessId -Force
$startup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$created=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$parent.CommandLine;CurrentDirectory=$auraRoot;ProcessStartupInformation=$startup}
$evidence.created=$created | Select-Object ProcessId,ReturnValue
$evidence | ConvertTo-Json -Depth 15 | Set-Content (Join-Path $taskRoot $(if($Rollback){'rollback.json'}else{'reload.json'})) -Encoding utf8
if ($created.ReturnValue -ne 0) {throw 'Launch failed; restore backup and service required'}
$evidence.created | ConvertTo-Json
