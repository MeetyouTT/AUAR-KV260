$ErrorActionPreference='Stop'
$adoptPath=Join-Path $PSScriptRoot 'service_processes.json'
$adoptRecords=Get-Content -LiteralPath $adoptPath -Raw -Encoding UTF8 | ConvertFrom-Json
function Get-AdoptTicks([object]$Value) {
    if ($Value -is [DateTime]) {return $Value.ToUniversalTime().Ticks}
    return [DateTimeOffset]::Parse([string]$Value,[Globalization.CultureInfo]::InvariantCulture).UtcDateTime.Ticks
}
foreach ($adoptPort in @('8812','8792')) {
    $adoptExpected=$adoptRecords.$adoptPort
    $adoptOwnerIds=@(Get-NetTCPConnection -State Listen -LocalPort ([int]$adoptPort) -ErrorAction Stop | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($adoptOwnerIds.Count -ne 1) {throw 'Service listener owner is not unique'}
    $adoptActual=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$adoptOwnerIds[0])
    if (-not $adoptActual -or -not $adoptActual.CommandLine.Contains('"'+$adoptExpected.entry+'"')) {throw 'Service entry differs'}
    if ($adoptActual.ProcessId -eq $adoptExpected.pid) {
        if ($adoptActual.CreationDate.ToUniversalTime().Ticks -ne (Get-AdoptTicks $adoptExpected.creation_utc)) {throw 'Service PID reused'}
        continue
    }
    $adoptAncestor=$adoptActual;$adoptProved=$false
    for ($adoptDepth=0;$adoptDepth -lt 8;$adoptDepth++) {
        $adoptAncestor=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$adoptAncestor.ParentProcessId)
        if (-not $adoptAncestor) {break}
        if ($adoptAncestor.ProcessId -eq $adoptExpected.pid) {
            if ($adoptAncestor.CreationDate.ToUniversalTime().Ticks -ne (Get-AdoptTicks $adoptExpected.creation_utc) -or
              $adoptAncestor.CommandLine -ne $adoptExpected.command_line -or $adoptAncestor.ExecutablePath -ne $adoptExpected.exe) {throw 'Launcher ownership changed'}
            $adoptProved=$true;break
        }
    }
    if (-not $adoptProved -or $adoptActual.CreationDate.ToUniversalTime().Ticks -lt (Get-AdoptTicks $adoptExpected.creation_utc)) {throw 'Cannot prove owned virtualenv child'}
    $adoptLauncher=[pscustomobject]@{pid=$adoptExpected.pid;creation_utc=$adoptExpected.creation_utc;exe=$adoptExpected.exe;command_line=$adoptExpected.command_line}
    $adoptValue=[pscustomobject]@{pid=$adoptActual.ProcessId;creation_utc=$adoptActual.CreationDate.ToUniversalTime().ToString('o');
      exe=$adoptActual.ExecutablePath;command_line=$adoptActual.CommandLine;entry=$adoptExpected.entry;
      port=[int]$adoptPort;launch_python=$adoptExpected.launch_python;launcher=$adoptLauncher;ownership='verified listener and exact created-launcher ancestry'}
    $adoptRecords | Add-Member -NotePropertyName $adoptPort -NotePropertyValue $adoptValue -Force
}
$adoptRecords | ConvertTo-Json -Depth 8 | Out-File -LiteralPath $adoptPath -Encoding utf8
[pscustomobject]@{status='OWNERSHIP_RESOLVED';voice_pid=$adoptRecords.'8792'.pid;hub_pid=$adoptRecords.'8812'.pid;processes_stopped=0} | ConvertTo-Json -Compress
