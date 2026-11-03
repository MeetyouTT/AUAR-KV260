param([ValidateSet('voice','hub')][string]$Group,[switch]$Stop,[switch]$AllowAbsent)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$entryPath=if ($Group -eq 'voice') {Join-Path $projectRoot 'aura\tools\board_model_host.py'} else {Join-Path (Split-Path -Parent $PSScriptRoot) '2026-10-28_device_skills\launch_hub.py'}
$servicePort=if ($Group -eq 'voice') {8792} else {8812}
$processList=Get-CimInstance Win32_Process
$roots=@($processList | Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -and $_.CommandLine.Contains($entryPath)})
$ownedIds=@($roots | ForEach-Object {[uint32]$_.ProcessId})
if ($ownedIds.Count -gt 2) {throw 'Unexpected duplicate service owners'}
if (-not $ownedIds.Count -and -not $AllowAbsent) {throw 'Expected service owner missing'}
$listeners=@(Get-NetTCPConnection -State Listen -LocalPort $servicePort -ErrorAction SilentlyContinue)
if (@($listeners | Where-Object {$_.OwningProcess -notin $ownedIds}).Count) {throw 'Unknown listener; preserve it'}
if ($ownedIds.Count) {
    do {
        $children=@($processList | Where-Object {$_.ParentProcessId -in $ownedIds -and $_.ProcessId -notin $ownedIds})
        $ownedIds+=@($children | ForEach-Object {[uint32]$_.ProcessId})
    } while ($children.Count)
}
$owned=@($processList | Where-Object {$_.ProcessId -in $ownedIds})
if (@($owned | Where-Object {$_.Name -notin @('python.exe','pythonw.exe','conhost.exe')}).Count) {throw 'Unknown descendant; preserve it'}
if (@($owned | Where-Object {$_.Name -eq 'conhost.exe' -and $_.ExecutablePath -ne 'C:\Windows\System32\conhost.exe'}).Count) {throw 'Unknown console owner'}
$pythonIds=@($owned | Where-Object {$_.Name -in @('python.exe','pythonw.exe')} | ForEach-Object {[uint32]$_.ProcessId})
if ($Stop) {
    [array]::Reverse($pythonIds)
    foreach ($serviceId in $pythonIds) {Stop-Process -Id $serviceId -Force -ErrorAction SilentlyContinue}
}
[pscustomobject]@{group=$Group;port=$servicePort;owned_python_ids=$pythonIds;stopped=[bool]$Stop;other_models_stopped=$false} | ConvertTo-Json -Compress
