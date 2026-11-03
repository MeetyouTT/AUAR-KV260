param([ValidatePattern('^[A-Za-z0-9_-]+\.json$')][string]$Receipt='layout_daemon_start.json')
$ErrorActionPreference='Stop'
$projectDaemonPython='C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$projectDaemonEntry=Join-Path $PSScriptRoot 'run_project_daemon.py'
$projectDaemonStartup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$projectDaemonCommand='"'+$projectDaemonPython+'" -B "'+$projectDaemonEntry+'" --receipt '+$Receipt
$projectDaemonCreated=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$projectDaemonCommand;CurrentDirectory=$PSScriptRoot;ProcessStartupInformation=$projectDaemonStartup}
if ($projectDaemonCreated.ReturnValue -ne 0) {throw 'Independent project daemon launcher creation failed'}
$projectDaemonCreated | Select-Object ProcessId,ReturnValue | ConvertTo-Json -Compress
