$ErrorActionPreference='Stop'
$projectStopBaseline=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime_owners_before.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$projectStopExpected=$projectStopBaseline.'11435'
$projectStopCurrent=Join-Path $PSScriptRoot 'layout_stop_owner.json'
if (Test-Path -LiteralPath $projectStopCurrent) {$projectStopExpected=Get-Content -LiteralPath $projectStopCurrent -Raw -Encoding UTF8 | ConvertFrom-Json}
$projectStopOther=$projectStopBaseline.'11434'
$projectStopIds=@(Get-NetTCPConnection -State Listen -LocalPort 11435 -ErrorAction Stop | Select-Object -ExpandProperty OwningProcess -Unique)
if ($projectStopIds.Count -ne 1 -or $projectStopIds[0] -ne $projectStopExpected.pid -or $projectStopIds[0] -eq $projectStopOther.pid) {throw 'Project daemon listener changed'}
$projectStopProcess=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$projectStopExpected.pid)
$projectStopTime=if ($projectStopExpected.creation_utc -is [DateTime]) {$projectStopExpected.creation_utc.ToUniversalTime()} else {[DateTimeOffset]::Parse([string]$projectStopExpected.creation_utc,[Globalization.CultureInfo]::InvariantCulture).UtcDateTime}
if (-not $projectStopProcess -or $projectStopProcess.CreationDate.ToUniversalTime().Ticks -ne $projectStopTime.Ticks -or
 $projectStopProcess.ExecutablePath -ne $projectStopExpected.exe -or $projectStopProcess.CommandLine -ne $projectStopExpected.command_line) {throw 'Project daemon ownership changed'}
$projectStopModels=Invoke-RestMethod -Uri 'http://127.0.0.1:11435/api/ps' -TimeoutSec 3
if (@($projectStopModels.models).Count -ne 0) {throw 'Project runner still resident; stop aborted'}
$projectStopOtherProcess=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$projectStopOther.pid)
if (-not $projectStopOtherProcess -or $projectStopOtherProcess.CommandLine -ne $projectStopOther.command_line) {throw 'Other Ollama changed; stop aborted'}
Stop-Process -Id $projectStopExpected.pid -ErrorAction Stop
[pscustomobject]@{status='STOPPED_ONLY_PROJECT_DAEMON';pid=$projectStopExpected.pid;other_ollama_pid_preserved=$projectStopOther.pid} | ConvertTo-Json -Compress
