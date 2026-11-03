$ErrorActionPreference='Stop'
$portraitPython='C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$portraitEntry=Join-Path $PSScriptRoot 'host_entry.py'
$portraitConfig=Join-Path $PSScriptRoot '../../aura/config/portrait_host.local.json'
$portraitHealth=Join-Path $PSScriptRoot 'host_health.py'
$portraitRecord=Join-Path $PSScriptRoot 'host_process.json'
$portraitListener=@(Get-NetTCPConnection -State Listen -LocalPort 8796 -ErrorAction SilentlyContinue)
if ($portraitListener.Count) {
    if (-not (Test-Path -LiteralPath $portraitRecord)) {throw 'Unowned portrait listener; no process stopped'}
    $portraitExisting=Get-Content -LiteralPath $portraitRecord -Raw -Encoding UTF8 | ConvertFrom-Json
    $portraitOwner=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$portraitExisting.pid)
    if (-not $portraitOwner -or $portraitOwner.CommandLine -notlike ('*"'+$portraitEntry+'"*') -or
        $portraitOwner.CreationDate.ToUniversalTime().ToString('o') -ne $portraitExisting.creation_utc -or
        @($portraitListener.OwningProcess | Select-Object -Unique).Count -ne 1 -or
        $portraitListener[0].OwningProcess -ne $portraitOwner.ProcessId) {throw 'Portrait ownership differs'}
    & $portraitPython -B $portraitHealth
    if ($LASTEXITCODE -ne 0) {throw 'Existing portrait listener is incompatible'}
    return
}
$portraitStartup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$portraitCommand='"'+$portraitPython+'" -B "'+$portraitEntry+'" --config "'+$portraitConfig+'"'
$portraitLaunched=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$portraitCommand;CurrentDirectory=$PSScriptRoot;ProcessStartupInformation=$portraitStartup}
if ($portraitLaunched.ReturnValue -ne 0) {throw 'Portrait process creation failed'}
$portraitOwner=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$portraitLaunched.ProcessId)
if (-not $portraitOwner) {throw 'New portrait process exited'}
[pscustomobject]@{pid=$portraitLaunched.ProcessId;entry=$portraitEntry;config=$portraitConfig;python=$portraitPython;
 creation_utc=$portraitOwner.CreationDate.ToUniversalTime().ToString('o');cpu_only=$true;creation='independent hidden WMI'} |
 ConvertTo-Json | Out-File -LiteralPath $portraitRecord -Encoding utf8
$portraitDeadline=[DateTime]::UtcNow.AddSeconds(60)
while ([DateTime]::UtcNow -lt $portraitDeadline) {
    if (-not (Get-Process -Id $portraitLaunched.ProcessId -ErrorAction SilentlyContinue)) {throw 'Portrait process exited; inspect host_stderr.log'}
    $portraitPreviousAction=$ErrorActionPreference
    try {$ErrorActionPreference='Continue';$portraitOutput=& $portraitPython -B $portraitHealth --quiet 2>$null;$portraitCode=$LASTEXITCODE}
    finally {$ErrorActionPreference=$portraitPreviousAction}
    if ($portraitCode -eq 0) {$portraitOutput;return}
    Start-Sleep -Milliseconds 300
}
throw 'Portrait readiness timeout; inspect only the owned process'
