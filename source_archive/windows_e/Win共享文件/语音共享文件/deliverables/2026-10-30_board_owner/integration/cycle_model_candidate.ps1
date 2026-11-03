$ErrorActionPreference = 'Stop'
$taskBase = 'E:\Win共享文件\语音共享文件\deliverables\2026-10-30_board_owner\integration'
$previousId = '1df9870181f44080ab6803de10ccb94b'
$previousFolder = Join-Path $taskBase ('resume_live\' + $previousId)
$previousState = Get-Content -LiteralPath (Join-Path $previousFolder 'status.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($previousState.session_id -ne $previousId -or $previousState.status -ne 'READY') { throw 'Expected current bounded candidate READY' }
$oldProcess = Get-CimInstance Win32_Process -Filter 'ProcessId=14832'
if (-not $oldProcess -or $oldProcess.CommandLine -notlike ('*model_candidate_runner.py*--session-id ' + $previousId + '*')) { throw 'Candidate process binding changed' }
$stopPath = Join-Path $previousFolder 'STOP'
$stopStream = [System.IO.File]::Open($stopPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write)
$stopStream.Dispose()
$closeDeadline = [DateTime]::UtcNow.AddSeconds(30)
do {
    Start-Sleep -Milliseconds 200
    $previousState = Get-Content -LiteralPath (Join-Path $previousFolder 'status.json') -Raw -Encoding UTF8 | ConvertFrom-Json
} while ($previousState.status -eq 'READY' -and [DateTime]::UtcNow -lt $closeDeadline)
if ($previousState.status -ne 'CLOSED' -or -not $previousState.owned_tts_closed -or -not $previousState.server_closed) { throw 'Previous candidate did not gracefully close' }
if (Get-NetTCPConnection -LocalPort 8797 -State Listen -ErrorAction SilentlyContinue) { throw 'Candidate port remains occupied' }
$nextId = [Guid]::NewGuid().ToString('N')
$voicePython = 'C:\Users\35870\.codex\visualizations\2026\10\09\01a12110-3ba4-7651-b3d7-2e6560916eb6\omnivoice-runtime-py310\Scripts\python.exe'
$runner = Join-Path $taskBase 'model_candidate_runner.py'
$outFile = Join-Path $taskBase ('resume_live\' + $nextId + '.stdout.log')
$errFile = Join-Path $taskBase ('resume_live\' + $nextId + '.stderr.log')
$launched = Start-Process -FilePath $voicePython -ArgumentList @('-B', ('"' + $runner + '"'), '--session-id', $nextId, '--lifetime-seconds', '7200') -WindowStyle Hidden -PassThru -RedirectStandardOutput $outFile -RedirectStandardError $errFile
$receipt = [ordered]@{status='OWN_CANDIDATE_GRACEFULLY_CYCLED_NEW_STARTING';previous_session=$previousId;previous_closed=$true;session_id=$nextId;launcher_pid=$launched.Id;status_path=(Join-Path $taskBase ('resume_live\' + $nextId + '\status.json'));unrelated_models_stopped=$false;fixed_daemon_stopped=$false;utc=[DateTime]::UtcNow.ToString('o')}
$receipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskBase 'resume_live\latest_cycle.json') -Encoding UTF8
$receipt | ConvertTo-Json
