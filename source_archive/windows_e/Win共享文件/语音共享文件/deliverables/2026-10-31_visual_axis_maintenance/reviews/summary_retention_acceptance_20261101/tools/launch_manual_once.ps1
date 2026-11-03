param([switch]$Execute)
$ErrorActionPreference = 'Stop'
$axisTaskPath = 'E:\Win共享文件\语音共享文件\deliverables\2026-10-31_visual_axis_maintenance\reviews\summary_retention_acceptance_20261101'
$axisDriverPath = Join-Path $axisTaskPath 'tools\start_manual_one_turn.py'
if (-not $Execute) {
    [ordered]@{ status='LOCAL_LAUNCH_PLAN_ONLY'; driver=$axisDriverPath; device_accessed=$false } | ConvertTo-Json -Compress
    exit 0
}
$axisLogPath = Join-Path $axisTaskPath ('evidence\manual_launcher_' + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
$null = New-Item -ItemType Directory -Path $axisLogPath
$axisStdoutPath = Join-Path $axisLogPath 'metadata_stdout.jsonl'
$axisStderrPath = Join-Path $axisLogPath 'local_stderr.log'
$axisProcess = Start-Process -FilePath 'D:\py312\python.exe' -ArgumentList @('-u','-B',('"' + $axisDriverPath + '"'),'--execute') -WorkingDirectory $axisTaskPath -WindowStyle Hidden -RedirectStandardOutput $axisStdoutPath -RedirectStandardError $axisStderrPath -PassThru
$axisLaunch = [ordered]@{
    status='FROZEN_MANUAL_DRIVER_LAUNCHED'; local_driver_pid=$axisProcess.Id
    stdout=$axisStdoutPath; stderr=$axisStderrPath; driver=$axisDriverPath
    utc=[DateTimeOffset]::UtcNow.ToString('o'); additional_device_commands_sent=$false
}
$axisLaunch | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $axisLogPath 'LAUNCH.json') -Encoding utf8
$axisDeadline = [DateTimeOffset]::UtcNow.AddSeconds(8)
while ([DateTimeOffset]::UtcNow -lt $axisDeadline) {
    if (Test-Path -LiteralPath $axisStdoutPath) {
        $axisLines = @(Get-Content -LiteralPath $axisStdoutPath -Encoding utf8)
        foreach ($axisLine in $axisLines) {
            if (-not $axisLine) { continue }
            try { $axisRow = $axisLine | ConvertFrom-Json } catch { continue }
            if ($axisRow.status -eq 'MANUAL_READY_FOR_ONE_NEW_TURN') {
                [ordered]@{ status=$axisRow.status; ready=$axisRow.ready; control_file=$axisRow.control_file; max_recording_seconds=$axisRow.max_recording_seconds; launch_directory=$axisLogPath; local_driver_pid=$axisProcess.Id } | ConvertTo-Json -Compress
                exit 0
            }
        }
    }
    $axisProcess.Refresh()
    if ($axisProcess.HasExited) {
        [ordered]@{ status='MANUAL_DRIVER_EXITED_WITHOUT_READY'; exit_code=$axisProcess.ExitCode; launch_directory=$axisLogPath } | ConvertTo-Json -Compress
        exit 1
    }
    Start-Sleep -Milliseconds 50
}
[ordered]@{ status='MANUAL_STARTUP_PENDING'; launch_directory=$axisLogPath; local_driver_pid=$axisProcess.Id } | ConvertTo-Json -Compress
