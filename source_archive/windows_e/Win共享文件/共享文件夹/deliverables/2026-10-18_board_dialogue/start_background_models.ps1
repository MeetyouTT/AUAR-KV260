param([string]$VoicePython='')
$ErrorActionPreference='Stop'
$modelTaskRoot=$PSScriptRoot
$modelProject=Split-Path -Parent (Split-Path -Parent $modelTaskRoot)
$modelConfig=Get-Content -LiteralPath (Join-Path $modelProject 'deliverables/2026-10-11_omnivoice_dialogue/stage_config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$modelPython=if ($VoicePython) {$VoicePython} else {[string]$modelConfig.voice.python}
if (-not (Test-Path -LiteralPath $modelPython -PathType Leaf)) {throw 'Pass -VoicePython with the actual voice environment Python path'}
$modelLauncher=Join-Path $modelTaskRoot 'launch_models.py'
$modelStartup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$modelCommand='"'+$modelPython+'" -B "'+$modelLauncher+'" --voice-python "'+$modelPython+'"'
$modelLaunched=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$modelCommand;CurrentDirectory=$modelProject;ProcessStartupInformation=$modelStartup}
if ($modelLaunched.ReturnValue -ne 0) {throw ('WMI process creation failed: '+$modelLaunched.ReturnValue)}
[pscustomobject]@{launcher_pid=$modelLaunched.ProcessId;creation='WMI independent parent';scheduled_task_created=$false;window='hidden'} | ConvertTo-Json | Out-File -LiteralPath (Join-Path $modelTaskRoot 'background_launch.json') -Encoding utf8
Get-Content -LiteralPath (Join-Path $modelTaskRoot 'background_launch.json')
