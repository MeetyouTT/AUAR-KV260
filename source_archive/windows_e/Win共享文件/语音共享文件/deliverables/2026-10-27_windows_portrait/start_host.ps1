$ErrorActionPreference='Stop'
$portraitPython='C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$portraitEntry=Join-Path $PSScriptRoot 'host_entry.py'
$portraitConfig=Join-Path $PSScriptRoot 'host_config.json'
$portraitHealth=Join-Path $PSScriptRoot 'host_health.py'
$portraitRecord=Join-Path $PSScriptRoot 'host_process.json'
$portraitProbe=New-Object System.Net.Sockets.TcpClient
try { $portraitProbe.Connect('192.168.50.1',8796);$portraitListening=$true } catch { $portraitListening=$false } finally { $portraitProbe.Dispose() }
if ($portraitListening) {
    if (-not (Test-Path -LiteralPath $portraitRecord)) { throw 'Unowned portrait port; no process will be stopped' }
    $portraitExisting=Get-Content -LiteralPath $portraitRecord -Raw -Encoding UTF8 | ConvertFrom-Json
    $portraitOwner=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$portraitExisting.pid)
    if (-not $portraitOwner -or $portraitOwner.CommandLine -notlike ('*'+$portraitEntry+'*')) { throw 'Portrait ownership differs' }
    & $portraitPython -B $portraitHealth
    if ($LASTEXITCODE -ne 0) { throw 'Existing portrait service is incompatible; no restart performed' }
    return
}
$portraitStartup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$portraitCommand='"'+$portraitPython+'" -B "'+$portraitEntry+'" --config "'+$portraitConfig+'"'
$portraitLaunched=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$portraitCommand;CurrentDirectory=$PSScriptRoot;ProcessStartupInformation=$portraitStartup}
if ($portraitLaunched.ReturnValue -ne 0) { throw 'Portrait background creation failed' }
[pscustomobject]@{pid=$portraitLaunched.ProcessId;entry=$portraitEntry;python=$portraitPython;config=$portraitConfig;cpu_only=$true;creation='WMI independent hidden parent'} |
    ConvertTo-Json | Out-File -LiteralPath $portraitRecord -Encoding utf8
$portraitDeadline=[DateTime]::UtcNow.AddSeconds(60)
while ([DateTime]::UtcNow -lt $portraitDeadline) {
    if (-not (Get-Process -Id $portraitLaunched.ProcessId -ErrorAction SilentlyContinue)) { throw 'Portrait process exited; inspect host_stderr.log' }
    $portraitPriorAction=$ErrorActionPreference
    try {
        $ErrorActionPreference='Continue'
        $portraitOutput=& $portraitPython -B $portraitHealth --quiet 2>$null
        $portraitHealthCode=$LASTEXITCODE
    } finally { $ErrorActionPreference=$portraitPriorAction }
    if ($portraitHealthCode -eq 0) { $portraitOutput;return }
    Start-Sleep -Milliseconds 300
}
throw 'Portrait readiness timeout; inspect existing owned process before retrying'
