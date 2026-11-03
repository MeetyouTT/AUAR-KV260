$ErrorActionPreference = 'Stop'
$sharedRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$workspaceRoot = Split-Path -Parent $sharedRoot
$pythonCandidates = @(
    (Join-Path $workspaceRoot 'tmp\aura-validation-venv\Scripts\python.exe'),
    (Join-Path $sharedRoot 'aura\.venv\Scripts\python.exe')
)
$systemPython = Get-Command python.exe -ErrorAction SilentlyContinue
if ($systemPython) { $pythonCandidates += $systemPython.Source }
foreach ($candidate in $pythonCandidates) {
    if (-not (Test-Path -LiteralPath $candidate)) { continue }
    try { $base = & $candidate -B -c 'import sys; print(sys.base_prefix)' 2>$null }
    catch { continue }
    if ($LASTEXITCODE -ne 0 -or -not $base) { continue }
    $tclPath = Join-Path $base 'tcl\tcl8.6'
    $tkPath = Join-Path $base 'tcl\tk8.6'
    if (Test-Path -LiteralPath (Join-Path $tclPath 'init.tcl')) { $env:TCL_LIBRARY = $tclPath }
    if (Test-Path -LiteralPath (Join-Path $tkPath 'tk.tcl')) { $env:TK_LIBRARY = $tkPath }
    $windowMode = '--window'
    try { $ready = & $candidate -B -c 'import tkinter, PIL; tkinter.Tcl(); print(12345)' 2>$null }
    catch { $ready = $null }
    if ($LASTEXITCODE -ne 0 -or $ready -notcontains '12345') {
        try { $ready = & $candidate -B -c 'import PySide6, PIL; print(12345)' 2>$null }
        catch { continue }
        if ($LASTEXITCODE -ne 0 -or $ready -notcontains '12345') { continue }
        $windowMode = '--qt-window'
    }
    $windowPython = Join-Path (Split-Path -Parent $candidate) 'pythonw.exe'
    if (-not (Test-Path -LiteralPath $windowPython)) { $windowPython = $candidate }
    $previewScript = Join-Path $PSScriptRoot 'preview_script.py'
    $process = Start-Process -FilePath $windowPython -ArgumentList @('-B', ('"' + $previewScript + '"'), $windowMode) -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardError (Join-Path $PSScriptRoot 'window_stderr.log') -PassThru
    Write-Output ('REUSE_PREVIEW_STARTED_PID=' + $process.Id)
    exit 0
}
throw 'No usable Python with Pillow and Tk or Qt was found.'
