$ErrorActionPreference='Stop'
$verifyPython='C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$verifyScript=Join-Path $PSScriptRoot 'verify_private_final.py'
$verifyStartup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$verifyCommand='"'+$verifyPython+'" -B "'+$verifyScript+'"'
$verifyResult=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$verifyCommand;CurrentDirectory=$PSScriptRoot;ProcessStartupInformation=$verifyStartup}
if ($verifyResult.ReturnValue -ne 0) {throw 'Private verification process failed to start'}
$verifyResult | Select-Object ProcessId,ReturnValue | ConvertTo-Json -Compress
