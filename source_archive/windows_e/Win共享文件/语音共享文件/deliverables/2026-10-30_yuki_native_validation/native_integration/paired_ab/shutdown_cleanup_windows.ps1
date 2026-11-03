$ErrorActionPreference = 'Stop'
$abDir = $PSScriptRoot
$fixtureState = Get-Content -LiteralPath (Join-Path $abDir 'isolated-host-state.json') -Raw | ConvertFrom-Json
$fixtureReady = Get-Content -LiteralPath $fixtureState.ready_file -Raw | ConvertFrom-Json
$fixtureProcess = Get-CimInstance Win32_Process -Filter 'ProcessId=32652'
$before = $fixtureProcess | Select-Object ProcessId,ParentProcessId,CreationDate,Name,ExecutablePath,CommandLine
$expectedScript = Join-Path $abDir 'isolated_portrait_server.py'
if ($fixtureProcess) {
    if ($fixtureState.pid -ne 32652 -or $fixtureReady.pid -ne 32652) { throw 'Fixture PID record mismatch' }
    if ($fixtureProcess.CreationDate.ToUniversalTime().ToString('o') -ne '2026-10-30T13:55:55.5169260Z') { throw 'Fixture PID creation time changed' }
    if (-not $fixtureProcess.CommandLine.Contains($expectedScript) -or -not $fixtureProcess.CommandLine.Contains($fixtureState.ready_file)) { throw 'Fixture command identity mismatch' }
    if ($fixtureProcess.ExecutablePath -ne $fixtureState.command[0]) { throw 'Fixture executable mismatch' }
    Stop-Process -Id 32652 -ErrorAction Stop
    Wait-Process -Id 32652 -Timeout 5 -ErrorAction SilentlyContinue
}
$after = Get-CimInstance Win32_Process -Filter 'ProcessId=32652'
$listeners = @(Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -eq 61584 -or $_.LocalPort -eq 8796 } | Select-Object LocalAddress,LocalPort,OwningProcess)
$production = Get-CimInstance Win32_Process -Filter 'ProcessId=26024' | Select-Object ProcessId,CreationDate,CommandLine
$report = [ordered]@{
    status = $(if (-not $after -and -not ($listeners | Where-Object { $_.LocalPort -eq 61584 }) -and ($listeners | Where-Object { $_.LocalPort -eq 8796 -and $_.OwningProcess -eq 26024 })) { 'PASS' } else { 'FAIL' })
    at_utc = (Get-Date).ToUniversalTime().ToString('o')
    owned_fixture_before = $before
    owned_fixture_pid_after = $after.ProcessId
    listener_after = $listeners
    production_8796_after = $production
    production_process_stopped = $false
    task_scope = 'Only independently launched A/B portrait fixture; no production service or model changes'
}
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $abDir 'shutdown-windows-cleanup.json') -Encoding utf8
$report | ConvertTo-Json -Depth 8
if ($report.status -ne 'PASS') { throw 'Cleanup verification failed' }
