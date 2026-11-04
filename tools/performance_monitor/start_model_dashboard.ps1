param(
    [string]$VoicePython = '',
    [string]$ProjectRoot = '',
    [switch]$Snapshot,
    [string]$SnapshotPath = '',
    [string]$Screenshot = '',
    [int]$CloseAfter = 0,
    [ValidateSet('overview', 'windows', 'board', 'inventory')]
    [string]$View = 'overview'
)
$ErrorActionPreference = 'Stop'
$bundleRoot = $PSScriptRoot
$dashboardScript = Join-Path $bundleRoot 'aura\tools\model_runtime_dashboard.py'

# An existing AURA root supplies model names and process attribution only.
if ($ProjectRoot) {
    $resolvedProject = (Resolve-Path -LiteralPath $ProjectRoot).Path
    if (-not (Test-Path -LiteralPath $resolvedProject -PathType Container)) {
        throw 'ProjectRoot must be a directory.'
    }
    $env:AURA_MONITOR_PROJECT = $resolvedProject
}
$projectForConfig = if ($env:AURA_MONITOR_PROJECT) { $env:AURA_MONITOR_PROJECT } else { $bundleRoot }
$consolePython = $VoicePython
if (-not $consolePython) {
    $configPath = Join-Path $projectForConfig 'aura\config\model_inference.local.json'
    if (Test-Path -LiteralPath $configPath) {
        $localConfig = Get-Content -Raw -Encoding UTF8 -LiteralPath $configPath | ConvertFrom-Json
        if ($localConfig.voice_python -and (Test-Path -LiteralPath $localConfig.voice_python)) {
            $consolePython = [string]$localConfig.voice_python
        }
    }
}
if (-not $consolePython) {
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($launcher) {
        $candidate = & $launcher.Source -3 -c 'import sys; print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $candidate) { $consolePython = [string]$candidate }
    }
}
if (-not $consolePython) {
    $candidate = Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($candidate -and $candidate.Source -notlike '*\WindowsApps\*') {
        $consolePython = $candidate.Source
    }
}
if (-not $consolePython -or -not (Test-Path -LiteralPath $consolePython -PathType Leaf)) {
    throw 'Install Python 3.9+ with Tcl/Tk, or pass -VoicePython C:\path\to\python.exe.'
}
$consolePython = (Resolve-Path -LiteralPath $consolePython).Path
if ((Split-Path -Leaf $consolePython) -ieq 'pythonw.exe') {
    $consolePython = Join-Path (Split-Path -Parent $consolePython) 'python.exe'
}

if ($Snapshot) {
    if (-not $SnapshotPath) {
        $SnapshotPath = Join-Path $bundleRoot 'aura\output\runtime_dashboard_snapshot.json'
    }
    & $consolePython -B -X utf8 $dashboardScript --snapshot $SnapshotPath
    exit $LASTEXITCODE
}

$windowPython = Join-Path (Split-Path -Parent $consolePython) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $windowPython)) { $windowPython = $consolePython }
$dashboardArgs = @('-B', '-X', 'utf8', ('"' + $dashboardScript + '"'), '--view', $View)
if ($Screenshot) { $dashboardArgs += @('--screenshot', ('"' + $Screenshot + '"')) }
if ($CloseAfter -gt 0) { $dashboardArgs += @('--close-after', [string]$CloseAfter) }
$dashboardProcess = Start-Process -FilePath $windowPython -ArgumentList $dashboardArgs -WorkingDirectory $bundleRoot -WindowStyle Hidden -PassThru
[pscustomobject]@{ pid = $dashboardProcess.Id; title = 'AURA dual-device performance monitor'; readOnly = $true }
