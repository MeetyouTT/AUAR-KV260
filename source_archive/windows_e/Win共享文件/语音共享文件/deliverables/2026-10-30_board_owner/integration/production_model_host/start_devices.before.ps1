param()
$ErrorActionPreference='Stop'
$devicePython='C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$deviceScript=Join-Path $PSScriptRoot 'start_devices.py'
$deviceStartup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$deviceCommand='"'+$devicePython+'" -B "'+$deviceScript+'"'
$deviceLaunched=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$deviceCommand;CurrentDirectory=$PSScriptRoot;ProcessStartupInformation=$deviceStartup}
if ($deviceLaunched.ReturnValue -ne 0) {throw 'Device launcher creation failed'}
$deviceLaunched | Select-Object ProcessId,ReturnValue | ConvertTo-Json
