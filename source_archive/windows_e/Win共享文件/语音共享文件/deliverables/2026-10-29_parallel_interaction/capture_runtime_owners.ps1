$ErrorActionPreference='Stop'
$parallelPorts=@(8792,8812,11435,11434)
$parallelRecords=@{}
foreach ($parallelPort in $parallelPorts) {
    $parallelListeners=@(Get-NetTCPConnection -State Listen -LocalPort $parallelPort -ErrorAction Stop)
    $parallelOwners=@($parallelListeners.OwningProcess | Select-Object -Unique)
    if ($parallelOwners.Count -ne 1) {throw ('Ambiguous owner on '+$parallelPort)}
    $parallelProcess=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$parallelOwners[0])
    if (-not $parallelProcess) {throw ('Owner missing on '+$parallelPort)}
    $parallelRecords[[string]$parallelPort]=[ordered]@{pid=$parallelProcess.ProcessId;creation_utc=$parallelProcess.CreationDate.ToUniversalTime().ToString('o');
      exe=$parallelProcess.ExecutablePath;command_line=$parallelProcess.CommandLine;listeners=@($parallelListeners | Select-Object LocalAddress,LocalPort,OwningProcess)}
}
$parallelPath=Join-Path $PSScriptRoot 'runtime_owners_before.json'
if (Test-Path -LiteralPath $parallelPath) {throw 'Preserve the original ownership record'}
$parallelRecords | ConvertTo-Json -Depth 7 | Out-File -LiteralPath $parallelPath -Encoding utf8
[pscustomobject]@{status='CAPTURED';ports=$parallelPorts;processes_stopped=0} | ConvertTo-Json -Compress
