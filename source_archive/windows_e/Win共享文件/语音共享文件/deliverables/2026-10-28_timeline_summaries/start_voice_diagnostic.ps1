param()
$ErrorActionPreference='Stop'
$summaryProject=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$summaryOld=Join-Path (Split-Path -Parent $PSScriptRoot) '2026-10-18_board_dialogue'
$summaryConfig=Get-Content -LiteralPath (Join-Path $summaryProject 'deliverables/2026-10-11_omnivoice_dialogue/stage_config.json') -Raw -Encoding utf8 | ConvertFrom-Json
$summaryPython=[string]$summaryConfig.voice.python
$summaryLauncher=Join-Path $PSScriptRoot 'launch_models_diagnostic.py'
$summaryRun=[guid]::NewGuid().ToString('N')
$summaryStartup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$summaryCommand='"'+$summaryPython+'" -B "'+$summaryLauncher+'" --voice-python "'+$summaryPython+'" --run-id '+$summaryRun
$summaryCreated=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$summaryCommand;CurrentDirectory=$summaryProject;ProcessStartupInformation=$summaryStartup}
if ($summaryCreated.ReturnValue -ne 0) {throw 'Diagnostic launcher creation failed'}
$summaryDeadline=[DateTime]::UtcNow.AddSeconds(420)
while ([DateTime]::UtcNow -lt $summaryDeadline) {
    $summaryState=$null
    try {$summaryState=Get-Content -LiteralPath (Join-Path $summaryOld 'models_launch.json') -Raw -Encoding utf8 | ConvertFrom-Json} catch {}
    if ($summaryState -and $summaryState.run_id -eq $summaryRun) {
        if ($summaryState.status -eq 'READY' -and $summaryState.ready) {$summaryState | ConvertTo-Json -Depth 6;return}
        if ($summaryState.status -eq 'FAILED') {throw ('Diagnostic startup failed: '+$summaryState.error)}
    }
    Start-Sleep -Milliseconds 500
}
throw 'Diagnostic wrapper readiness timeout'
