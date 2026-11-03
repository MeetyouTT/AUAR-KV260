$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$baseline=Get-Content -LiteralPath (Join-Path $taskRoot 'baseline.json') -Raw -Encoding utf8 | ConvertFrom-Json
$suite=[xml](Get-Content -LiteralPath (Join-Path $taskRoot 'tests.xml') -Raw -Encoding utf8)
foreach($node in $suite.SelectNodes('//testsuite')) {
    if ([int]$node.failures -ne 0 -or [int]$node.errors -ne 0) {throw 'Regression gate failed'}
}
& 'D:\py312\python.exe' -B (Join-Path $taskRoot 'maintenance.py') guard
if ($LASTEXITCODE -ne 0) {throw 'Board idle/concurrency gate failed'}
function Assert-OwnedListener([int]$port) {
    $oldPort=@($baseline.owners.listeners | Where-Object {$_.LocalPort -eq $port})[0]
    $oldProcess=@($baseline.owners.processes | Where-Object {$_.pid -eq $oldPort.OwningProcess})[0]
    $current=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$oldProcess.pid)
    $listener=@(Get-NetTCPConnection -State Listen -LocalPort $port | Where-Object {$_.OwningProcess -eq $oldProcess.pid})
    if (-not $current -or -not $listener -or $current.CommandLine -cne $oldProcess.command_line -or
        $current.ExecutablePath -cne $oldProcess.exe -or
        $current.CreationDate.ToUniversalTime().Ticks -ne ([datetime]$oldProcess.creation_utc).ToUniversalTime().Ticks) {throw ('Owner changed: '+$port)}
    return $current
}
$voiceOwner=Assert-OwnedListener 8792
$hubOwner=Assert-OwnedListener 8812
$visualOwner=Assert-OwnedListener 8810
if ($visualOwner.CommandLine -notmatch [regex]::Escape('D:\AIModels\qwen3-vl-2b-interaction\') -or
    $visualOwner.CommandLine -notmatch '--alias aura-vision' -or $visualOwner.CommandLine -notmatch '--port 8810') {throw 'Visual model scope mismatch'}
$taskReceipt=Join-Path $taskRoot 'services_deployment.json'
if (Test-Path -LiteralPath $taskReceipt) {throw 'Do not replay service deployment'}
$receipt=[ordered]@{status='RELOADING';stopped_visual_pid=$visualOwner.ProcessId;stopped_voice_pid=$voiceOwner.ProcessId;stopped_hub_pid=$hubOwner.ProcessId;model_files_deleted=$false}
$receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskReceipt -Encoding utf8
# Each parent is the known venv launcher of this exact entry, not another service.
$wrappers=@()
foreach($owned in @($voiceOwner,$hubOwner)) {
    $wrapper=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$owned.ParentProcessId)
    if ($wrapper -and ($wrapper.CommandLine -match '2026-10-29_parallel_interaction[\\/]voice_entry.py' -or $wrapper.CommandLine -match '2026-10-29_parallel_interaction[\\/]hub_entry.py')) {$wrappers+=$wrapper}
}
Stop-Process -Id $visualOwner.ProcessId -ErrorAction Stop
Stop-Process -Id $voiceOwner.ProcessId -ErrorAction Stop
Stop-Process -Id $hubOwner.ProcessId -ErrorAction Stop
foreach($wrapper in $wrappers) {
    $still=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$wrapper.ProcessId)
    if ($still -and $still.CommandLine -ceq $wrapper.CommandLine -and $still.CreationDate -eq $wrapper.CreationDate) {Stop-Process -Id $still.ProcessId -ErrorAction Stop}
}
$voicePython='C:\Users\35870\.codex\visualizations\2026\10\09\01a12110-3ba4-7651-b3d7-2e6560916eb6\omnivoice-runtime-py310\Scripts\python.exe'
$hubPython='D:\AIModels\speaker-identity\venv\Scripts\python.exe'
$serviceRoot=Join-Path (Split-Path -Parent $taskRoot) '2026-10-29_parallel_interaction'
$voiceEntry=Join-Path $serviceRoot 'voice_entry.py'
$hubEntry=Join-Path $serviceRoot 'hub_entry.py'
$voiceData=Join-Path (Split-Path -Parent $taskRoot) '2026-10-18_board_dialogue\model_host'
$deadline=[DateTime]::UtcNow.AddSeconds(300).ToString("yyyy-MM-ddTHH:mm:ss.ffffff'Z'")
$voiceCommand='"'+$voicePython+'" -B -u "'+$voiceEntry+'" --listen 192.168.50.1 --port 8792 --root "'+$voiceData+'" --voice-python "'+$voicePython+'" --startup-deadline-utc "'+$deadline+'"'
$hubCommand='"'+$hubPython+'" -B -u "'+$hubEntry+'" --root "C:\Users\35870\AppData\Local\Aura\device-memory" --speaker-model "D:/AIModels/speaker-identity/ecapa"'
function Launch-Hidden([string]$command) {
    $startup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
    $result=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$command;CurrentDirectory=$serviceRoot;ProcessStartupInformation=$startup}
    if ($result.ReturnValue -ne 0) {throw 'Owned service launch failed'}
    return [int]$result.ProcessId
}
$receipt.hub_launcher_pid=Launch-Hidden $hubCommand
$receipt.voice_launcher_pid=Launch-Hidden $voiceCommand
$receipt.startup_deadline_utc=$deadline
$receipt.status='STARTING'
$receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskReceipt -Encoding utf8
$receipt | ConvertTo-Json -Depth 5 -Compress
