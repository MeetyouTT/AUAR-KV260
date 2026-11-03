param(
    [switch]$Snapshot,
    [string]$Screenshot,
    [int]$CloseAfter = 0
)
$ErrorActionPreference = 'Stop'
$dashboardRoot = $PSScriptRoot
$dashboardPythonRoot = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python'
$dashboardPython = Join-Path $dashboardPythonRoot 'pythonw.exe'
$dashboardScript = Join-Path $dashboardRoot 'aura\tools\model_runtime_dashboard.py'
if (-not (Test-Path -LiteralPath $dashboardPython)) {
    throw "Dashboard Python is missing: $dashboardPython"
}
if ($Snapshot) {
    $dashboardConsole = Join-Path $dashboardPythonRoot 'python.exe'
    $dashboardProof = Join-Path $dashboardRoot 'deliverables\2026-10-30_runtime_dashboard\manual_snapshot.json'
    & $dashboardConsole -B -X utf8 $dashboardScript --snapshot $dashboardProof
    exit $LASTEXITCODE
}
$dashboardArgs = @('-B', '-X', 'utf8', ('"' + $dashboardScript + '"'))
if ($Screenshot) { $dashboardArgs += @('--screenshot', ('"' + $Screenshot + '"')) }
if ($CloseAfter -gt 0) { $dashboardArgs += @('--close-after', [string]$CloseAfter) }
# Hide the helper console. Tk creates the separately visible dashboard window.
$dashboardProcess = Start-Process -FilePath $dashboardPython -ArgumentList $dashboardArgs -WorkingDirectory $dashboardRoot -WindowStyle Hidden -PassThru
[pscustomobject]@{ pid=$dashboardProcess.Id; title='AURA model runtime dashboard'; readOnly=$true }
