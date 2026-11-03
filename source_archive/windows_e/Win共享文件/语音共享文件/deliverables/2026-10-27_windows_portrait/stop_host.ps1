$ErrorActionPreference='Stop'
$portraitRecord=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'host_process.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$portraitOwner=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$portraitRecord.pid)
if (-not $portraitOwner) { Write-Host 'Owned portrait process already stopped';return }
if ($portraitOwner.CommandLine -notlike ('*'+$portraitRecord.entry+'*') -or $portraitOwner.CommandLine -notlike ('*'+$portraitRecord.config+'*')) { throw 'Ownership differs; no process stopped' }
Stop-Process -Id $portraitOwner.ProcessId -Force
Write-Host 'Owned CPU portrait service stopped'
