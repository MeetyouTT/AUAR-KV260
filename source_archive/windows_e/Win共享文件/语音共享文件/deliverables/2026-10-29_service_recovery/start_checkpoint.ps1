param([ValidatePattern('^[0-9a-f]{32}$')][string]$Job,[ValidateSet('before','after')][string]$Phase)
$ErrorActionPreference='Stop'
$checkpointPython='C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$checkpointScript=Join-Path $PSScriptRoot 'db_checkpoint.py'
$checkpointStartup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$checkpointCommand='"'+$checkpointPython+'" -B "'+$checkpointScript+'" --job-id '+$Job+' --phase '+$Phase
$checkpointResult=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$checkpointCommand;CurrentDirectory=$PSScriptRoot;ProcessStartupInformation=$checkpointStartup}
if ($checkpointResult.ReturnValue -ne 0) {throw 'Checkpoint process creation failed'}
$checkpointResult | Select-Object ProcessId,ReturnValue | ConvertTo-Json -Compress
