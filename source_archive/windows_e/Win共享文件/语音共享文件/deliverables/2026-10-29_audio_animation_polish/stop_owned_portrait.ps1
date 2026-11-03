$ErrorActionPreference='Stop'
$portraitRecord=Join-Path $PSScriptRoot 'host_process.json'
if (-not (Test-Path -LiteralPath $portraitRecord)) {throw 'Owned portrait record missing'}
$portraitExpected=Get-Content -LiteralPath $portraitRecord -Raw -Encoding UTF8 | ConvertFrom-Json
$portraitOwner=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$portraitExpected.pid)
if (-not $portraitOwner) {return}
if ($portraitOwner.CommandLine -notlike ('*"'+$portraitExpected.entry+'"*') -or
 $portraitOwner.CreationDate.ToUniversalTime().ToString('o') -ne $portraitExpected.creation_utc) {throw 'Portrait owner changed; refusing stop'}
Stop-Process -Id $portraitExpected.pid -ErrorAction Stop
