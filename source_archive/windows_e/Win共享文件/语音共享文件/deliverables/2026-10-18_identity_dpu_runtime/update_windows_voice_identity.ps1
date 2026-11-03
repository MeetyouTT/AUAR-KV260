param([string]$VoicePython='')
$ErrorActionPreference='Stop'
$voiceTask=$PSScriptRoot
$voiceRoot=Split-Path -Parent (Split-Path -Parent $voiceTask)
$voiceManifest=Get-Content -LiteralPath (Join-Path $voiceTask 'windows_source_manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$voiceConfig=Get-Content -LiteralPath (Join-Path $voiceRoot 'aura/config/board_dialogue_model.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$voiceRecords=@()
foreach ($voiceItem in $voiceManifest.files) {
    $voiceSource=Join-Path (Join-Path $voiceTask 'windows_source') $voiceItem.path
    $voiceTarget=Join-Path (Join-Path $voiceRoot 'aura') $voiceItem.path
    $voiceHash=(Get-FileHash -LiteralPath $voiceSource -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($voiceHash -ne $voiceItem.sha256) {throw ('Update source SHA mismatch: '+$voiceItem.path)}
    $voiceBefore=$null
    if (Test-Path -LiteralPath $voiceTarget) {
        $voiceBefore=(Get-FileHash -LiteralPath $voiceTarget -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($voiceBefore -ne $voiceItem.sha256 -and $voiceBefore -ne $voiceItem.allowed_before_sha256) {
            throw ('Local source has newer/unrecognized changes; preserve it and merge first: '+$voiceItem.path)
        }
    }
    $voiceRecords+= [pscustomobject]@{path=$voiceItem.path;source=$voiceSource;target=$voiceTarget;before=$voiceBefore;after=$voiceHash}
}
$voiceHealth=$null
try {$voiceHealth=Invoke-RestMethod -Uri 'http://192.168.50.1:8792/health' -TimeoutSec 3} catch {}
if ($voiceHealth -and $voiceHealth.busy) {throw 'End the current dialogue before updating the voice service.'}
$voiceListeners=@(Get-NetTCPConnection -LocalPort 8792 -State Listen -ErrorAction SilentlyContinue)
$voiceOwners=@($voiceListeners | Select-Object -ExpandProperty OwningProcess -Unique)
if ($voiceOwners.Count -gt 1) {throw 'Multiple 8792 owners; no process was changed.'}
$voiceProcess=$null
if ($voiceOwners.Count -eq 1) {
    $voiceProcess=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$voiceOwners[0])
    $voiceExpected=Join-Path $voiceRoot 'aura/tools/board_model_host.py'
    if (-not $voiceProcess.CommandLine -or $voiceProcess.CommandLine -notmatch [regex]::Escape($voiceExpected)) {
        throw 'Port 8792 belongs to an unrecognized process; no process was changed.'
    }
}
$voiceStamp=Get-Date -Format 'yyyyMMddTHHmmssfff'
$voiceBackup=Join-Path $voiceTask ('windows-backup-'+$voiceStamp)
New-Item -ItemType Directory -Path $voiceBackup | Out-Null
foreach ($voiceRecord in $voiceRecords) {
    if ($voiceRecord.before) {
        $voiceSaved=Join-Path $voiceBackup $voiceRecord.path
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $voiceSaved) | Out-Null
        Copy-Item -LiteralPath $voiceRecord.target -Destination $voiceSaved
    }
}
$voiceRecords | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $voiceBackup 'sources.json') -Encoding UTF8
$voiceAlreadyReady=$voiceHealth -and $voiceHealth.ready -and $voiceHealth.voice_text_channel
if ($voiceProcess -and -not $voiceAlreadyReady) {
    & taskkill.exe /PID ([int]$voiceProcess.ProcessId) /T /F | Out-Null
    if ($LASTEXITCODE -ne 0) {throw 'Could not stop the verified voice host; sources remain backed up.'}
    $voiceStopDeadline=(Get-Date).AddSeconds(15)
    do {
        $voiceStillListening=@(Get-NetTCPConnection -LocalPort 8792 -State Listen -ErrorAction SilentlyContinue)
        if ($voiceStillListening.Count -eq 0) {break}
        Start-Sleep -Milliseconds 300
    } while ((Get-Date) -lt $voiceStopDeadline)
    if ($voiceStillListening.Count) {throw '8792 did not stop; no replacement listener was started.'}
}
foreach ($voiceRecord in $voiceRecords) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $voiceRecord.target) | Out-Null
    Copy-Item -LiteralPath $voiceRecord.source -Destination $voiceRecord.target -Force
    if ((Get-FileHash -LiteralPath $voiceRecord.target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $voiceRecord.after) {
        throw ('Installed source SHA mismatch: '+$voiceRecord.path)
    }
}
if (-not $voiceAlreadyReady) {& (Join-Path $voiceRoot 'start_voice.ps1') -VoicePython $VoicePython}
$voiceDeadline=(Get-Date).AddSeconds(180)
$voiceReady=$false
do {
    try {
        $voiceNewHealth=Invoke-RestMethod -Uri 'http://192.168.50.1:8792/health' -TimeoutSec 3
        if ($voiceNewHealth.ready -and $voiceNewHealth.voice_text_channel -and $voiceNewHealth.llm_model -eq $voiceConfig.model) {
            $voiceReady=$true;break
        }
    } catch {}
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $voiceDeadline)
$voiceResult=[pscustomobject]@{status=$(if ($voiceReady) {'PASS_VOICE_TEXT_CHANNEL_READY'} else {'NOT_READY_CHECK_SERVICE_LOGS'});backup=$voiceBackup;voice_text_channel=$voiceReady;model=[string]$voiceConfig.model;model_weights_changed=$false;board_deployment_performed=$false}
$voiceResult | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $voiceTask 'windows-update-result.json') -Encoding UTF8
$voiceResult | ConvertTo-Json -Depth 5
if (-not $voiceReady) {throw 'The new voice interface is not ready yet. Check service logs; do not claim enrollment is enabled.'}
