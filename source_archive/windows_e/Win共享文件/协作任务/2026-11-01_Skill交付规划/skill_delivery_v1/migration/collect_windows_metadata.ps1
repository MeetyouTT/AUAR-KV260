param(
    [Parameter(Mandatory=$true)][string]$Output,
    [string]$PlatformId = 'rtx5090_desktop_migration',
    [string]$PythonExe = ''
)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $Output) { throw 'Receipt already exists; choose a new output file.' }
$receipt = [ordered]@{
    schema = 'aura.windows_environment.v1'
    platform_id = $PlatformId
    recorded_utc = [DateTime]::UtcNow.ToString('o')
    user_reported_gpu = 'Desktop RTX 5090'
    file_migration_state = 'IN_PROGRESS_USER_REPORTED'
    current_service_health_queried = $false
    model_loaded = $false
    microphone_opened = $false
    gpu_query_status = 'NOT_AVAILABLE'
}
$osInfo = Get-CimInstance -ClassName Win32_OperatingSystem
$receipt.os = [ordered]@{caption=$osInfo.Caption;version=$osInfo.Version;build=$osInfo.BuildNumber}
$receipt.cpu = @(Get-CimInstance -ClassName Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors)
$gpuTool = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($null -ne $gpuTool) {
    $gpuLines = & $gpuTool.Source '--query-gpu=name,memory.total,memory.used,memory.free,driver_version,uuid' '--format=csv,noheader,nounits' 2>&1
    $gpuExit = $LASTEXITCODE
    $receipt.gpu_query_exit_code = $gpuExit
    if ($gpuExit -eq 0) {
        $receipt.gpu = @($gpuLines | ConvertFrom-Csv -Header name,memory_total_mib,memory_used_mib,memory_free_mib,driver_version,uuid)
        $receipt.gpu_query_status = 'COLLECTED_NOT_MODEL_ACCEPTANCE'
    } else {
        $receipt.gpu_query_status = 'FAILED'
        $receipt.gpu_query_error = (($gpuLines | Out-String).Trim())
    }
}
if ($PythonExe) {
    if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) { throw 'PythonExe must be the selected existing interpreter.' }
    $pyMetadata = & $PythonExe '-c' 'import sys,platform,json;print(json.dumps({"executable":sys.executable,"version":platform.python_version()}))'
    if ($LASTEXITCODE -ne 0) { throw 'Selected Python metadata probe failed.' }
    $receipt.python = $pyMetadata | ConvertFrom-Json
} else {
    $receipt.python = $null
}
$receipt.status = 'METADATA_COLLECTED_MIGRATION_ACCEPTANCE_PENDING'
$parent = Split-Path -Parent $Output
if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
$receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Output -Encoding UTF8
Write-Output ('Saved metadata only: ' + $Output)
