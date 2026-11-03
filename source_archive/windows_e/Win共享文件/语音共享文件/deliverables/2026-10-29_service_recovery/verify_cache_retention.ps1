$ErrorActionPreference='Stop'
$taskPython='C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$taskScript=Join-Path $PSScriptRoot 'verify_cache_retention.py'
$taskReport=Join-Path $PSScriptRoot 'cache_retention_verification.json'
if (Test-Path -LiteralPath $taskReport) {throw 'Inspect existing retention proof before repeating'}
$taskCommand='"'+$taskPython+'" -B "'+$taskScript+'"'
$taskStartup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$taskCreated=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$taskCommand;CurrentDirectory=$PSScriptRoot;ProcessStartupInformation=$taskStartup}
if ($taskCreated.ReturnValue -ne 0) {throw 'Private retention proof launch failed'}
$taskLimit=[DateTime]::UtcNow.AddSeconds(30)
while (-not (Test-Path -LiteralPath $taskReport) -and [DateTime]::UtcNow -lt $taskLimit) {Start-Sleep -Milliseconds 200}
$taskValue=Get-Content -LiteralPath $taskReport -Raw -Encoding UTF8 | ConvertFrom-Json
if ($taskValue.status -ne 'PASS') {throw ('Retention proof failed: '+$taskValue.error)}
[PSCustomObject]@{status=$taskValue.status;cache_before=$taskValue.cache_before;cache_after=$taskValue.cache_after;removed_count=$taskValue.removed_count;visual_archive_unchanged=$taskValue.visual_archive_and_revision_tables_unchanged} | ConvertTo-Json -Compress
