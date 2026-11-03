<#
zz_v3_next.ps1  -  ASCII ONLY (PowerShell 5.1 reads BOM-less UTF-8 as ANSI; all non-ASCII paths come in as command-line params).

What it does:
  1) sleeps until -RunAt (HH:mm, today) unless already past;
  2) waits until the v3 batch stops producing (no new submit log for -IdleSec and ComfyUI queue empty), capped by -MaxWaitMin;
  3) structural check: every workflows\*_api.json must have raw\<id>\ with 39 png + meta.json (state=ok, frame_count=39);
  4) runs the numeric QC script (read-only) and writes a human-readable report to -Report.

Guardrails: never touches frames, never writes aura\assets, never submits new jobs.
#>
param(
    [Parameter(Mandatory = $true)][string]$Py,
    [Parameter(Mandatory = $true)][string]$QcScript,
    [Parameter(Mandatory = $true)][string]$BatchRoot,
    [Parameter(Mandatory = $true)][string]$Log,
    [string]$RunAt = '',
    [string]$Report = '',
    [int]$PollSec = 60,
    [int]$IdleSec = 240,
    [int]$MaxWaitMin = 180
)

$ErrorActionPreference = 'Continue'
if (-not $Report) { $Report = $Log }

function W([string]$m) {
    $line = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + ' ' + $m
    Add-Content -LiteralPath $Log -Value $line -Encoding UTF8
}

W ('START runAt=' + $RunAt + ' batch=' + $BatchRoot)

# --- 1) wait until RunAt ------------------------------------------------
if ($RunAt) {
    $p = $RunAt.Split(':')
    $target = (Get-Date).Date.AddHours([int]$p[0]).AddMinutes([int]$p[1])
    while ((Get-Date) -lt $target) {
        $s = [int][math]::Ceiling(($target - (Get-Date)).TotalSeconds)
        if ($s -gt 300) { $s = 300 }
        if ($s -lt 1) { $s = 1 }
        Start-Sleep -Seconds $s
    }
    W 'reached run time'
}

# --- 2) wait for batch idle --------------------------------------------
$rawDir = Join-Path $BatchRoot 'raw'
$logDir = Join-Path $BatchRoot 'logs'
$deadline = (Get-Date).AddMinutes($MaxWaitMin)
while ($true) {
    $last = Get-ChildItem -LiteralPath $logDir -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime | Select-Object -Last 1
    $idle = 999999
    if ($last) { $idle = [int]((Get-Date) - $last.LastWriteTime).TotalSeconds }
    $q = -1
    try { $q = @((Invoke-RestMethod -Uri 'http://127.0.0.1:8188/queue' -TimeoutSec 10).queue_running).Count }
    catch { $q = -1 }
    $full = @(Get-ChildItem -LiteralPath $rawDir -Directory -ErrorAction SilentlyContinue |
        Where-Object { @(Get-ChildItem -LiteralPath $_.FullName -File -Filter *.png).Count -eq 39 }).Count
    W ('wait idle=' + $idle + 's queue=' + $q + ' complete39=' + $full)
    if (($idle -ge $IdleSec) -and ($q -le 0)) { break }
    if ((Get-Date) -gt $deadline) { W 'WAIT_TIMEOUT'; break }
    Start-Sleep -Seconds $PollSec
}

# --- 3) structural check ----------------------------------------------
$wf = Join-Path $BatchRoot 'workflows'
$expected = @(Get-ChildItem -LiteralPath $wf -File -Filter '*_api.json' -ErrorAction SilentlyContinue |
    ForEach-Object { $_.Name -replace '_api\.json$', '' } | Sort-Object)
W ('expected_api_graphs=' + $expected.Count)

$res = @()
foreach ($name in $expected) {
    $dir = Join-Path $rawDir $name
    $png = 0; $state = 'NO_META'; $frames = ''
    if (Test-Path -LiteralPath $dir) {
        $png = @(Get-ChildItem -LiteralPath $dir -File -Filter *.png -ErrorAction SilentlyContinue).Count
        $mp = Join-Path $dir 'meta.json'
        if (Test-Path -LiteralPath $mp) {
            try {
                $j = Get-Content -LiteralPath $mp -Raw -Encoding UTF8 | ConvertFrom-Json
                $state = [string]$j.state
                $frames = [string]$j.frame_count
            }
            catch { $state = 'META_PARSE_ERR' }
        }
    }
    $ok = (($png -eq 39) -and ($state -eq 'ok') -and ($frames -eq '39'))
    $res += [pscustomobject]@{ id = $name; png = $png; state = $state; meta_frames = $frames; ok = $ok }
}
$badList = @($res | Where-Object { -not $_.ok })
W ('structure ok=' + (@($res | Where-Object { $_.ok }).Count) + ' bad=' + $badList.Count)

# --- 4) numeric QC -----------------------------------------------------
$qcOut = & $Py -s -B $QcScript --batch-root $BatchRoot 2>&1
$qcRc = $LASTEXITCODE
W ('qc rc=' + $qcRc + ' lines=' + @($qcOut).Count)

# --- report ------------------------------------------------------------
$lines = @()
$lines += 'batch_root   = ' + $BatchRoot
$lines += 'generated_at = ' + (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
$lines += 'api_graphs   = ' + $expected.Count + '  raw_OK = ' + (@($res | Where-Object { $_.ok }).Count) + '  raw_BAD = ' + $badList.Count
$lines += ''
$lines += '[structure]'
$lines += ($res | ForEach-Object { '  ' + $_.id + '  png=' + $_.png + '  state=' + $_.state + '  meta_frames=' + $_.meta_frames + '  ok=' + $_.ok })
if ($badList.Count -gt 0) {
    $lines += '  RESUBMIT_CMD_HINT: same submit command without --only runs only the missing/incomplete ids'
}
$lines += ''
$lines += '[numeric_qc] rc=' + $qcRc
$lines += ($qcOut | ForEach-Object { '  ' + [string]$_ })
$lines += ''
$lines += 'NOTE: STRUCTURE_VALID_REQUIRES_VISUAL_REVIEW is numeric only; visual spot-check still required.'
$lines += 'NEXT_DONE'
Set-Content -LiteralPath $Report -Value $lines -Encoding UTF8
W ('DONE report=' + $Report)
