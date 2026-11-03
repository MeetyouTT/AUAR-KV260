$ErrorActionPreference = 'Stop'
$workspaceRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$sharedRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$candidates = @(
    (Join-Path $workspaceRoot 'tmp\aura-validation-venv\Scripts\python.exe'),
    (Join-Path $sharedRoot 'aura\.venv\Scripts\python.exe')
)
$systemPython = Get-Command python.exe -ErrorAction SilentlyContinue
if ($systemPython) { $candidates += $systemPython.Source }
foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate) {
        Write-Output 'Open http://127.0.0.1:8771/'
        & $candidate -B (Join-Path $PSScriptRoot 'serve_preview.py') --port 8771
        exit $LASTEXITCODE
    }
}
throw 'Python 3 not found. Static preview requires only the Python standard library.'
