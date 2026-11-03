$ErrorActionPreference='Stop'
$motionProject=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$motionApp=Join-Path $motionProject 'aura'
$motionManifest=Get-Content (Join-Path $PSScriptRoot 'pc_action_manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$motionBefore=Invoke-RestMethod 'http://192.168.50.1:8792/health' -TimeoutSec 4
if (-not $motionBefore.ready -or $motionBefore.busy) {throw 'PC host not idle/ready'}
$motionState=Get-Content (Join-Path $PSScriptRoot 'pc_action_board_guard.json') -Raw -Encoding UTF8|ConvertFrom-Json
if ($motionState.phase -ne 'IDLE' -or $motionState.enabled -or $motionState.playing -or $motionState.pending) {throw 'Board guard not paused and idle'}
if (([DateTimeOffset]::UtcNow-[DateTimeOffset]$motionState.checked_at_utc).TotalSeconds -gt 15) {throw 'Board guard expired'}
$motionExpected=Join-Path $motionApp 'tools/board_model_host.py'
$motionPortOwner=(Get-NetTCPConnection -LocalPort 8792 -State Listen|Select-Object -First 1).OwningProcess
$motionProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$motionPortOwner"
if (-not $motionProcess.CommandLine.Contains($motionExpected)) {throw 'Unknown PC8792 owner'}
foreach($motionFile in $motionManifest.files.PSObject.Properties){
 $motionPath=Join-Path $motionApp $motionFile.Name
 if ((Get-FileHash $motionPath -Algorithm SHA256).Hash.ToLower() -ne $motionFile.Value.before_sha256) {throw ('Source changed: '+$motionFile.Name)}
}
foreach($motionFile in $motionManifest.config_sha256.PSObject.Properties){
 if ((Get-FileHash (Join-Path $motionApp $motionFile.Name) -Algorithm SHA256).Hash.ToLower() -ne $motionFile.Value) {throw ('Config changed: '+$motionFile.Name)}
}
$motionBackup=Join-Path $PSScriptRoot ('pc-before-actions-'+[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss'))
New-Item -ItemType Directory $motionBackup|Out-Null
foreach($motionFile in $motionManifest.files.PSObject.Properties){
 $motionPath=Join-Path $motionBackup $motionFile.Name
 New-Item -ItemType Directory (Split-Path $motionPath -Parent) -Force|Out-Null
 Copy-Item -LiteralPath (Join-Path $motionApp $motionFile.Name) -Destination $motionPath
}
function Stop-MotionOwnedHost {
 $motionAll=@(Get-CimInstance Win32_Process)
 $motionOwners=@($motionAll|Where-Object {$_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -and $_.CommandLine.Contains($motionExpected) -and $_.CommandLine -like '*--port 8792*'})
 $motionParents=@($motionOwners|ForEach-Object {$_.ProcessId});$motionDesc=@()
 while($motionParents.Count -gt 0){
  $motionNext=@($motionAll|Where-Object {$_.ParentProcessId -in $motionParents -and $_.ProcessId -notin @($motionDesc|ForEach-Object {$_.ProcessId})})
  $motionDesc+=$motionNext;$motionParents=@($motionNext|ForEach-Object {$_.ProcessId})
 }
 foreach($motionChild in @($motionDesc|Where-Object {$_.CommandLine -like '*omnivoice_voice.py*'})){Stop-Process -Id $motionChild.ProcessId -Force -ErrorAction SilentlyContinue}
 foreach($motionOwner in $motionOwners){Stop-Process -Id $motionOwner.ProcessId -Force -ErrorAction SilentlyContinue}
}
try {
 Stop-MotionOwnedHost
 foreach($motionFile in $motionManifest.files.PSObject.Properties){Copy-Item -LiteralPath (Join-Path (Join-Path $PSScriptRoot 'action_sources') $motionFile.Name) -Destination (Join-Path $motionApp $motionFile.Name)}
 & (Join-Path $motionProject 'deliverables/2026-10-18_board_dialogue/start_background_models.ps1')
 $motionDeadline=[DateTime]::UtcNow.AddSeconds(180);$motionAfter=$null
 do {
  try {$motionAfter=Invoke-RestMethod 'http://192.168.50.1:8792/health' -TimeoutSec 3;if($motionAfter.ready){break}}catch{}
  Start-Sleep -Seconds 2
 } while([DateTime]::UtcNow -lt $motionDeadline)
 if(-not $motionAfter.ready){throw 'New PC host did not become ready'}
 foreach($motionField in @('llm_model','asr_model','tts','num_step')){if($motionAfter.$motionField -ne $motionBefore.$motionField){throw ('Model changed: '+$motionField)}}
 if(($motionAfter.latency_options|ConvertTo-Json -Compress) -ne ($motionBefore.latency_options|ConvertTo-Json -Compress)){throw 'Latency options changed'}
 if($motionAfter.conversation_memory.memory_controls -ne 'explicit_conversation_facts_v1' -or -not $motionAfter.conversation_memory.persistent){throw 'Memory contract changed'}
 foreach($motionFile in $motionManifest.config_sha256.PSObject.Properties){if((Get-FileHash (Join-Path $motionApp $motionFile.Name) -Algorithm SHA256).Hash.ToLower() -ne $motionFile.Value){throw ('Config changed: '+$motionFile.Name)}}
 [pscustomobject]@{status='PC_ACTIONS_READY';backup=$motionBackup;before=$motionBefore;after=$motionAfter;files=$motionManifest.files}|ConvertTo-Json -Depth 20|Set-Content (Join-Path $PSScriptRoot 'pc_action_deployment.json') -Encoding UTF8
 Write-Output 'PC_ACTIONS_READY'
} catch {
 $motionFailure=$_.Exception.Message
 Stop-MotionOwnedHost
 foreach($motionFile in $motionManifest.files.PSObject.Properties){Copy-Item -LiteralPath (Join-Path $motionBackup $motionFile.Name) -Destination (Join-Path $motionApp $motionFile.Name)}
 & (Join-Path $motionProject 'deliverables/2026-10-18_board_dialogue/start_background_models.ps1')
 [pscustomobject]@{status='PC_ACTIONS_ROLLED_BACK';error=$motionFailure;backup=$motionBackup}|ConvertTo-Json|Set-Content (Join-Path $PSScriptRoot 'pc_action_deployment.json') -Encoding UTF8
 throw $motionFailure
}
