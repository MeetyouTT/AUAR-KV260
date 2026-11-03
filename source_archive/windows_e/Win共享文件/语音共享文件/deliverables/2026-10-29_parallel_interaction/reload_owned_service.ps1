param([ValidateSet(8792,8812)][int]$Port,[switch]$StopOnly)
$ErrorActionPreference='Stop'
$reloadProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$reloadBefore=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime_owners_before.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$reloadRecordPath=Join-Path $PSScriptRoot 'service_processes.json'
$reloadRecords=if (Test-Path -LiteralPath $reloadRecordPath) {Get-Content -LiteralPath $reloadRecordPath -Raw -Encoding UTF8 | ConvertFrom-Json} else {[pscustomobject]@{}}
$reloadKey=[string]$Port
$reloadExpected=if ($reloadRecords.PSObject.Properties.Name -contains $reloadKey) {$reloadRecords.$reloadKey} else {$reloadBefore.$reloadKey}
$reloadOwners=@(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
$reloadProcess=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$reloadExpected.pid)
if ($reloadProcess) {
    $reloadExpectedTime=if ($reloadExpected.creation_utc -is [DateTime]) {$reloadExpected.creation_utc.ToUniversalTime()} else {[DateTimeOffset]::Parse([string]$reloadExpected.creation_utc,[Globalization.CultureInfo]::InvariantCulture).UtcDateTime}
    if ($reloadProcess.CreationDate.ToUniversalTime().Ticks -ne $reloadExpectedTime.Ticks -or
      $reloadProcess.ExecutablePath -ne $reloadExpected.exe -or $reloadProcess.CommandLine -ne $reloadExpected.command_line -or
      ($reloadOwners.Count -and ($reloadOwners.Count -ne 1 -or $reloadOwners[0] -ne $reloadExpected.pid))) {throw 'Owned service changed; no process stopped'}
    Stop-Process -Id $reloadExpected.pid -ErrorAction Stop
} elseif ($reloadOwners.Count) {throw 'Unowned listener; no process stopped'}
if ($StopOnly) {
    [pscustomobject]@{status='STOPPED_OWNED_SERVICE';port=$Port;pid=$reloadExpected.pid;other_processes_stopped=0} | ConvertTo-Json -Compress
    return
}
if ($Port -eq 8792) {
    $reloadEntry=Join-Path $PSScriptRoot 'voice_entry.py'
    $reloadRoot=Join-Path $reloadProject 'deliverables/2026-10-18_board_dialogue/model_host'
    # Read the accepted exact runtime from the original command, not a guessed environment.
    $reloadVoiceMatch=[regex]::Match($reloadBefore.'8792'.command_line,'--voice-python\s+(?:"([^"]+)"|(\S+))')
    if (-not $reloadVoiceMatch.Success) {throw 'Accepted voice Python missing from original command'}
    $reloadVoicePython=if ($reloadVoiceMatch.Groups[1].Success) {$reloadVoiceMatch.Groups[1].Value} else {$reloadVoiceMatch.Groups[2].Value}
    $reloadLaunchConfig=Get-Content -LiteralPath (Join-Path $reloadProject 'deliverables/2026-10-11_omnivoice_dialogue/stage_config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $reloadPython=[string]$reloadLaunchConfig.voice.python
    $reloadArguments=' --listen 192.168.50.1 --port 8792 --root "'+$reloadRoot+'" --voice-python "'+$reloadVoicePython+'"'
    $reloadHostSource=Join-Path $reloadProject 'aura/tools/board_model_host.py'
    if ((Get-Content -LiteralPath $reloadHostSource -Raw -Encoding UTF8).Contains('--startup-deadline-utc')) {
        # Python 3.10's fromisoformat accepts microseconds, not .NET's 7 digits.
        $reloadDeadline=[DateTime]::UtcNow.AddSeconds(300).ToString("yyyy-MM-ddTHH:mm:ss.ffffff'Z'",[Globalization.CultureInfo]::InvariantCulture)
        $reloadArguments+=' --startup-deadline-utc "'+$reloadDeadline+'"'
    }
} else {
    $reloadEntry=Join-Path $PSScriptRoot 'hub_entry.py'
    $reloadStorage=Get-Content -LiteralPath (Join-Path $reloadProject 'aura/config/model_storage.local.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $reloadSpeakerParent=Split-Path -Parent ([IO.Path]::GetFullPath([string]$reloadStorage.speaker_directory))
    $reloadPython=Join-Path $reloadSpeakerParent 'venv/Scripts/python.exe'
    $reloadPrivate=Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Aura/device-memory'
    $reloadArguments=' --root "'+$reloadPrivate+'" --speaker-model "'+$reloadStorage.speaker_directory+'"'
}
if (-not (Test-Path -LiteralPath $reloadPython -PathType Leaf)) {throw 'Original service Python unavailable'}
$reloadStartup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$reloadCommand='"'+$reloadPython+'" -B -u "'+$reloadEntry+'"'+$reloadArguments
$reloadCreated=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$reloadCommand;CurrentDirectory=$reloadProject;ProcessStartupInformation=$reloadStartup}
if ($reloadCreated.ReturnValue -ne 0) {throw 'Owned service creation failed'}
$reloadNew=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$reloadCreated.ProcessId)
if (-not $reloadNew) {throw 'Owned service exited during creation'}
$reloadValue=[pscustomobject]@{pid=$reloadNew.ProcessId;creation_utc=$reloadNew.CreationDate.ToUniversalTime().ToString('o');
 exe=$reloadNew.ExecutablePath;command_line=$reloadNew.CommandLine;entry=$reloadEntry;port=$Port;launch_python=$reloadPython}
$reloadRecords | Add-Member -NotePropertyName $reloadKey -NotePropertyValue $reloadValue -Force
$reloadRecords | ConvertTo-Json -Depth 7 | Out-File -LiteralPath $reloadRecordPath -Encoding utf8
[pscustomobject]@{status='STARTING';port=$Port;pid=$reloadNew.ProcessId;only_owned_service_reloaded=$true;ready=$false} | ConvertTo-Json -Compress
