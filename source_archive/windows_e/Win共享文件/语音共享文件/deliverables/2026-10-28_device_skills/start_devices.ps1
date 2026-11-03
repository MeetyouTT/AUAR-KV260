param()
$ErrorActionPreference='Stop'
$deviceBusinessProject=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$deviceBusinessOwnerPath=Join-Path $deviceBusinessProject 'aura/config/business_owner.local.json'
if(Test-Path -LiteralPath $deviceBusinessOwnerPath){
    $deviceBusinessOwner=Get-Content -Raw -Encoding UTF8 -LiteralPath $deviceBusinessOwnerPath | ConvertFrom-Json
    if($deviceBusinessOwner.schema_version -ne 1 -or $deviceBusinessOwner.owner -notin @('board','windows')){throw 'Unknown business owner; legacy device business remains stopped'}
    if($deviceBusinessOwner.owner -eq 'board'){throw 'Board owns device and memory business. Use project start_inference.ps1 for Windows model execution only.'}
}
$devicePython='C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$deviceScript=Join-Path $PSScriptRoot 'start_devices.py'
$deviceStartup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$deviceCommand='"'+$devicePython+'" -B "'+$deviceScript+'"'
$deviceLaunched=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$deviceCommand;CurrentDirectory=$PSScriptRoot;ProcessStartupInformation=$deviceStartup}
if ($deviceLaunched.ReturnValue -ne 0) {throw 'Device launcher creation failed'}
$deviceLaunched | Select-Object ProcessId,ReturnValue | ConvertTo-Json
