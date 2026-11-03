param([string]$VoicePython='')
$ErrorActionPreference='Stop'
$modelTaskRoot=$PSScriptRoot
$modelProject=Split-Path -Parent (Split-Path -Parent $modelTaskRoot)
$modelConfig=Get-Content -LiteralPath (Join-Path $modelProject 'deliverables/2026-10-11_omnivoice_dialogue/stage_config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$modelPython=if ($VoicePython) {$VoicePython} else {[string]$modelConfig.voice.python}
if (-not (Test-Path -LiteralPath $modelPython -PathType Leaf)) {throw 'Pass -VoicePython with the actual voice environment Python path'}
$modelLauncher=Join-Path $modelTaskRoot 'launch_models.py'
$modelStartup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$modelRunId=[guid]::NewGuid().ToString('N')
$modelCommand='"'+$modelPython+'" -B "'+$modelLauncher+'" --voice-python "'+$modelPython+'" --run-id '+$modelRunId
$modelLaunched=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$modelCommand;CurrentDirectory=$modelProject;ProcessStartupInformation=$modelStartup}
if ($modelLaunched.ReturnValue -ne 0) {throw ('WMI process creation failed: '+$modelLaunched.ReturnValue)}
[pscustomobject]@{launcher_pid=$modelLaunched.ProcessId;run_id=$modelRunId;creation='WMI independent parent';scheduled_task_created=$false;window='hidden'} | ConvertTo-Json | Out-File -LiteralPath (Join-Path $modelTaskRoot 'background_launch.json') -Encoding utf8
$modelReceipt=Join-Path $modelTaskRoot 'models_launch.json'
$modelDeadline=[DateTime]::UtcNow.AddSeconds(420)
while ([DateTime]::UtcNow -lt $modelDeadline) {
    $modelState=$null
    if (Test-Path -LiteralPath $modelReceipt) {
        try { $modelState=Get-Content -LiteralPath $modelReceipt -Raw -Encoding UTF8 | ConvertFrom-Json } catch { }
    }
    if ($modelState -and $modelState.run_id -eq $modelRunId) {
        if ($modelState.status -eq 'READY' -and $modelState.ready) { $modelState | ConvertTo-Json -Depth 6; return }
        if ($modelState.status -eq 'FAILED') { throw ('Voice stack start failed: '+$modelState.error) }
    }
    if (-not (Get-Process -Id $modelLaunched.ProcessId -ErrorAction SilentlyContinue)) { throw 'Voice launcher exited before confirming readiness; inspect models_launch.json and service logs' }
    Start-Sleep -Milliseconds 500
}
throw 'Voice stack readiness timed out; inspect models_launch.json before retrying'
