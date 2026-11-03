# Read CPU/process/log metadata only. No inference, network, GPU probe or mutation.
$ErrorActionPreference = 'Stop'
$taskProjectDir = 'E:\Win共享文件\语音共享文件\deliverables\2026-10-18_board_dialogue'
$taskRecordPath = Join-Path $taskProjectDir 'project_ollama_process.json'
$taskLogPath = Join-Path $taskProjectDir 'project_ollama_stderr.log'
$taskRecorded = Get-Content -LiteralPath $taskRecordPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskDaemonId = [int]$taskRecorded.pid
$taskDaemon = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$taskDaemonId"
if ($null -eq $taskDaemon) { throw 'Recorded project daemon missing' }
$taskCreated = $taskDaemon.CreationDate.ToUniversalTime()
$taskExpectedCreated = [DateTimeOffset]::Parse([string]$taskRecorded.ownership.creation_utc).UtcDateTime
$taskOwnership = [pscustomobject]@{
    pid_matches = ([int]$taskRecorded.ownership.pid -eq $taskDaemonId)
    executable_matches = ([string]$taskDaemon.ExecutablePath -ieq [string]$taskRecorded.ownership.executable)
    command_line_matches = ([string]$taskDaemon.CommandLine -ceq [string]$taskRecorded.ownership.command_line)
    creation_time_matches = ([Math]::Abs(($taskCreated - $taskExpectedCreated).TotalMilliseconds) -lt 1)
    process_name_matches = ($taskDaemon.Name -ieq 'ollama.exe')
}
if (@($taskOwnership.PSObject.Properties | Where-Object { $_.Value -ne $true }).Count) {
    throw 'Recorded project daemon identity mismatch'
}

$taskCpu = @(Get-CimInstance -ClassName Win32_Processor | ForEach-Object {
    [pscustomobject]@{
        name = $_.Name.Trim()
        physical_cores = [int]$_.NumberOfCores
        enabled_cores = [int]$_.NumberOfEnabledCore
        logical_processors = [int]$_.NumberOfLogicalProcessors
        thread_count = [int]$_.ThreadCount
    }
})

function Read-TaskNumericArg([string]$command, [string]$long, [string]$short) {
    # Short options are case-sensitive: -c (context) differs from -C (CPU mask).
    $taskArgPattern = '(?:^|\s)(?:' + [regex]::Escape($long) + '|' + [regex]::Escape($short) + ')(?:[= ]+)(\d+)(?=\s|$)'
    $taskMatch = [regex]::Match($command, $taskArgPattern)
    if ($taskMatch.Success) { return [int]$taskMatch.Groups[1].Value }
    return $null
}

$taskRunners = @(Get-CimInstance -ClassName Win32_Process -Filter "ParentProcessId=$taskDaemonId" |
    Where-Object { $_.Name -ceq 'llama-server.exe' })
if ($taskRunners.Count -ne 1) { throw 'Expected one project llama-server child' }
$taskRunner = $taskRunners[0]
$taskCommand = [string]$taskRunner.CommandLine
$taskProcess = Get-Process -Id $taskRunner.ProcessId
$taskAllowedPattern = '(?:^|\s)(--cpu-(?:mask(?:-batch)?|range(?:-batch)?|strict(?:-batch)?)|-C|-Cr|-Cb|-Crb|--threads(?:-batch)?|-tb|-t|--prio(?:-batch)?|--poll(?:-batch)?)(?:[= ]+)(0x[0-9A-Fa-f]+|[0-9A-Fa-f,\-]+)(?=\s|$)'
$taskAllowed = @([regex]::Matches($taskCommand, $taskAllowedPattern) | ForEach-Object {
    [pscustomobject]@{ flag = $_.Groups[1].Value; value = $_.Groups[2].Value }
})
$taskRunnerMetadata = [pscustomobject]@{
    pid = [int]$taskRunner.ProcessId
    parent_pid = [int]$taskRunner.ParentProcessId
    created_utc = $taskRunner.CreationDate.ToUniversalTime().ToString('o')
    context_size = Read-TaskNumericArg $taskCommand '--ctx-size' '-c'
    runner_port = Read-TaskNumericArg $taskCommand '--port' '--port'
    explicit_generation_threads = Read-TaskNumericArg $taskCommand '--threads' '-t'
    explicit_prompt_threads = Read-TaskNumericArg $taskCommand '--threads-batch' '-tb'
    allowed_cpu_flags = $taskAllowed
    process_affinity_hex = $taskProcess.ProcessorAffinity.ToInt64().ToString('X')
    total_os_threads_is_not_decode_thread_count = $taskProcess.Threads.Count
    priority_class = [string]$taskProcess.PriorityClass
    model_path_in_project_external_store = ($taskCommand.Contains('D:\AIModels\Ollama-AURA') -or $taskCommand.Contains('D:\AIModels\qwen3.8-27b-abliterated'))
}

$taskLogStream = [IO.File]::Open($taskLogPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
try {
    # Capture one bounded prefix while allowing the running logger to append.
    $taskLogBytes = New-Object byte[] ([int]$taskLogStream.Length)
    $taskReadOffset = 0
    while ($taskReadOffset -lt $taskLogBytes.Length) {
        $taskReadCount = $taskLogStream.Read($taskLogBytes, $taskReadOffset, $taskLogBytes.Length - $taskReadOffset)
        if ($taskReadCount -le 0) { throw 'Log snapshot changed during read' }
        $taskReadOffset += $taskReadCount
    }
}
finally { $taskLogStream.Dispose() }
$taskHasher = [Security.Cryptography.SHA256]::Create()
try { $taskLogDigest = [BitConverter]::ToString($taskHasher.ComputeHash($taskLogBytes)).Replace('-', '').ToLowerInvariant() }
finally { $taskHasher.Dispose() }
$taskLogLines = [Text.Encoding]::UTF8.GetString($taskLogBytes) -split "`r?`n"
$taskHeaderIndex = -1
for ($taskIndex = $taskLogLines.Length - 1; $taskIndex -ge 0; $taskIndex--) {
    if ($taskLogLines[$taskIndex] -cmatch 'n_threads\s*=\s*\d+.*n_threads_batch\s*=\s*\d+') {
        $taskHeaderIndex = $taskIndex; break
    }
}
if ($taskHeaderIndex -lt 0) { throw 'No thread metadata found' }
$taskRows = @()
for ($taskIndex = [Math]::Max(0, $taskHeaderIndex - 50); $taskIndex -lt [Math]::Min($taskLogLines.Length, $taskHeaderIndex + 260); $taskIndex++) {
    $taskLine = $taskLogLines[$taskIndex]
    $taskRow = [ordered]@{ line = $taskIndex + 1 }
    if ($taskLine -match 'starting' -and $taskLine -match 'runner|llama') {
        $taskRow.event = 'runner_start'
        $taskTimeMatch = [regex]::Match($taskLine, '\d{4}-\d{2}-\d{2}T[0-9:.+\-]+')
        $taskPortMatch = [regex]::Match($taskLine, '--port[= ]+(\d+)')
        if ($taskTimeMatch.Success) { $taskRow.timestamp = $taskTimeMatch.Value }
        if ($taskPortMatch.Success) { $taskRow.port = [int]$taskPortMatch.Groups[1].Value }
    }
    if ($taskLine -cmatch 'n_threads\s*=' -or $taskLine -match 'system_info') {
        foreach ($taskMatch in [regex]::Matches($taskLine, '\b(n_threads_batch|n_threads|AVX2|AVX512|AVX512_VBMI|AVX512_VNNI|F16C|FMA|SSE3|SSSE3)\s*=\s*(\d+)')) {
            $taskRow[$taskMatch.Groups[1].Value] = [int]$taskMatch.Groups[2].Value
        }
    }
    if ($taskLine -match 'loaded CPU backend') {
        $taskDllMatch = [regex]::Match($taskLine, '(ggml-cpu[^\\/\s"'']*\.dll)')
        if ($taskDllMatch.Success) { $taskRow.cpu_backend_dll = $taskDllMatch.Value }
    }
    $taskLayersMatch = [regex]::Match($taskLine, 'offloaded\s+(\d+)/(\d+)\s+layers')
    if ($taskLayersMatch.Success) {
        $taskRow.gpu_layers = [int]$taskLayersMatch.Groups[1].Value
        $taskRow.all_layers = [int]$taskLayersMatch.Groups[2].Value
    }
    if ($taskRow.Count -gt 1) { $taskRows += [pscustomobject]$taskRow }
}
$taskStartRows = @($taskRows | Where-Object { $_.PSObject.Properties.Name -contains 'event' -and $_.event -eq 'runner_start' })
if ($taskStartRows.Count -ne 1) { throw 'Expected one recent runner start marker' }
$taskLogCreated = [DateTimeOffset]::Parse([string]$taskStartRows[0].timestamp).UtcDateTime
$taskProcessCreated = $taskRunner.CreationDate.ToUniversalTime()
$taskBinding = [pscustomobject]@{
    runner_port_matches_log = ($taskRunnerMetadata.runner_port -eq $taskStartRows[0].port)
    runner_creation_matches_log_within_1_second = ([Math]::Abs(($taskProcessCreated - $taskLogCreated).TotalMilliseconds) -lt 1000)
}
if (@($taskBinding.PSObject.Properties | Where-Object { $_.Value -ne $true }).Count) {
    throw 'Current runner does not match latest log metadata'
}

$taskEvidence = [ordered]@{
    status = 'PASS_READ_ONLY_CURRENT_CPU_THREAD_REVIEW'
    observed_utc = [DateTime]::UtcNow.ToString('o')
    cpu = $taskCpu
    project_daemon = @{ pid = $taskDaemonId; created_utc = $taskCreated.ToString('o'); record_matches = $taskOwnership }
    runner = $taskRunnerMetadata
    log_binding = $taskBinding
    log_snapshot = @{ path = $taskLogPath; bytes = $taskLogBytes.Length; sha256 = $taskLogDigest; latest_thread_header_line = $taskHeaderIndex + 1; metadata = $taskRows }
    raw_log_command_environment_prompt_reply_or_pcm_saved = $false
    inference_calls = 0
    gpu_probes = 0
    runtime_mutations = 0
}
$taskOutput = Join-Path $PSScriptRoot 'CPU_THREAD_EVIDENCE.json'
$taskEvidence | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $taskOutput -Encoding UTF8
$taskLoggedThreads = @($taskRows | Where-Object { $_.PSObject.Properties.Name -contains 'n_threads_batch' })[0]
[pscustomobject]@{ status = $taskEvidence.status; physical_cores = $taskCpu[0].physical_cores; logical_processors = $taskCpu[0].logical_processors; latest_logged_threads = $taskLoggedThreads.n_threads; latest_logged_prompt_threads = $taskLoggedThreads.n_threads_batch; runner_matches_log = $true; output = $taskOutput } | ConvertTo-Json -Compress
