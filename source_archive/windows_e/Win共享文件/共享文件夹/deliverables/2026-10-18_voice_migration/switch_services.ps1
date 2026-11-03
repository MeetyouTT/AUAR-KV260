$ErrorActionPreference='Stop'
$migrationSource=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$migrationTarget='E:\Win共享文件\语音共享文件'
$migrationResult=[ordered]@{status='STARTING';source=$migrationSource;destination=$migrationTarget;stopped_pids=@();board_services_restarted=$false;board_dialogue_memory='Host RAM history resets at model-service restart'}
$migrationReport=Join-Path $PSScriptRoot 'service_switch_start.json'
try {
    $migrationCopy=Get-Content -LiteralPath (Join-Path $migrationTarget 'deliverables/2026-10-18_voice_migration/copy_result.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($migrationCopy.status -ne 'PASS_ALL_COPIED_FILES_SHA256') {throw 'Project copy has not passed verification'}
    $migrationStates=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'board_before_switch.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $migrationUi=$migrationStates.ui.value
    if ($migrationUi.phase -ne 'IDLE' -or $migrationUi.playing -or $migrationUi.local_recording.state -eq 'RECORDING' -or $migrationUi.local_transcription.service.pending) {throw 'Board is busy; service switch postponed'}
    if ($migrationStates.host_voice.value.busy) {throw 'Voice host is busy'}
    $migrationProcesses=@(Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and $_.CommandLine.Contains($migrationSource) -and (
            $_.CommandLine.Contains('aura\tools\board_model_host.py') -or
            $_.CommandLine.Contains('aura\tools\asr_server.py') -or
            ($_.CommandLine.Contains('aura\board\runtime\audio\omnivoice_voice.py') -and $_.CommandLine.Contains('2026-10-18_board_dialogue\model_host'))
        )
    })
    $migrationResult.processes_before=@($migrationProcesses | Select-Object ProcessId,ParentProcessId,CommandLine)
    $migrationPids=@($migrationProcesses | Select-Object -ExpandProperty ProcessId)
    foreach ($migrationProcess in $migrationProcesses) {
        $migrationCurrent=Get-CimInstance Win32_Process -Filter ('ProcessId='+$migrationProcess.ProcessId) -ErrorAction SilentlyContinue
        if ($migrationCurrent -and $migrationCurrent.CommandLine -eq $migrationProcess.CommandLine) {
            Stop-Process -Id $migrationProcess.ProcessId -ErrorAction SilentlyContinue
            $migrationResult.stopped_pids+=@($migrationProcess.ProcessId)
        }
    }
    for ($migrationWait=0; $migrationWait -lt 20; $migrationWait++) {
        $migrationListeners=@(Get-NetTCPConnection -LocalAddress '192.168.50.1' -State Listen -ErrorAction SilentlyContinue | Where-Object {$_.LocalPort -in @(8791,8792)})
        if (-not $migrationListeners) {break}
        Start-Sleep -Milliseconds 500
    }
    if ($migrationListeners) {throw 'Model ports still occupied; new service not started'}
    & (Join-Path $migrationTarget 'start_voice.ps1')
    $migrationResult.status='TARGET_MODELS_STARTING'
} catch {
    $migrationResult.status='FAILED'
    $migrationResult.error=$_.Exception.Message
    if ($migrationResult.stopped_pids.Count -gt 0) {
        & (Join-Path $migrationSource 'deliverables/2026-10-18_board_dialogue/start_background_models.ps1')
        $migrationResult.rollback='Original D-drive launcher started; readiness needs verification'
    }
} finally {
    $migrationResult | ConvertTo-Json -Depth 7 | Out-File -LiteralPath $migrationReport -Encoding utf8
    Get-Content -LiteralPath $migrationReport
}
