$ErrorActionPreference='Stop'
$taskPython='C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$taskScript=Join-Path $PSScriptRoot 'verify_databases.py'
$taskReport=Join-Path $PSScriptRoot 'database_verification.json'
if (Test-Path -LiteralPath $taskReport) {throw 'Inspect existing database verification before repeating'}
$taskCommand='"'+$taskPython+'" -B "'+$taskScript+'"'
$taskStartup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$taskCreated=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$taskCommand;CurrentDirectory=$PSScriptRoot;ProcessStartupInformation=$taskStartup}
if ($taskCreated.ReturnValue -ne 0) {throw 'Independent database verification launch failed'}
$taskLimit=[DateTime]::UtcNow.AddSeconds(30)
while (-not (Test-Path -LiteralPath $taskReport) -and [DateTime]::UtcNow -lt $taskLimit) {Start-Sleep -Milliseconds 200}
$taskValue=Get-Content -LiteralPath $taskReport -Raw -Encoding UTF8 | ConvertFrom-Json
if ($taskValue.status -ne 'PASS') {throw ('Database verification requires inspection: '+$taskValue.error)}
[PSCustomObject]@{status=$taskValue.status;original_sources_unchanged=$taskValue.original_sources_unchanged;private_backups_only=$taskValue.private_backups_only} | ConvertTo-Json -Compress
