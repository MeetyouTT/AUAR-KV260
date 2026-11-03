$ErrorActionPreference='Stop'
$portraitPrior=Join-Path $PSScriptRoot '../2026-10-27_windows_portrait'
$portraitPriorEntry=[IO.Path]::GetFullPath((Join-Path $portraitPrior 'host_entry.py'))
$portraitPriorRecord=Get-Content -LiteralPath (Join-Path $portraitPrior 'host_process.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$portraitListeners=@(Get-NetTCPConnection -State Listen -LocalPort 8796 -ErrorAction Stop)
$portraitOwner=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$portraitPriorRecord.pid)
if (-not $portraitOwner -or $portraitOwner.CommandLine -notlike ('*"'+$portraitPriorEntry+'"*') -or
 @($portraitListeners.OwningProcess | Select-Object -Unique).Count -ne 1 -or
 $portraitListeners[0].OwningProcess -ne $portraitOwner.ProcessId) {throw 'Prior portrait listener is not the expected owned service'}
$portraitBefore=[pscustomobject]@{pid=$portraitOwner.ProcessId;creation_utc=$portraitOwner.CreationDate.ToUniversalTime().ToString('o');command_line=$portraitOwner.CommandLine}
$portraitBefore | ConvertTo-Json | Out-File -LiteralPath (Join-Path $PSScriptRoot 'previous_portrait_process.json') -Encoding utf8
$portraitRecheck=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$portraitBefore.pid)
if (-not $portraitRecheck -or $portraitRecheck.CreationDate.ToUniversalTime().ToString('o') -ne $portraitBefore.creation_utc -or
 $portraitRecheck.CommandLine -ne $portraitBefore.command_line) {throw 'Prior portrait changed during guard'}
Stop-Process -Id $portraitBefore.pid -ErrorAction Stop
& (Join-Path $PSScriptRoot 'start_host.ps1')
