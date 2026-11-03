# readback_docx.ps1 - inspect a rendered .docx via Microsoft Word COM.
# Purpose: project rule 3 "md and docx must be paired and read back consistently" and
# criterion 4 "every md has a same-name docx". The historical python readback script
# lived under C:\Users\Administrator\... and this host has no Python, so this is the
# local replacement.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\readback_docx.ps1 -Docx "<abs path.docx>"
#
# Output: paragraph count, table count, per-table row/col count and the number of rows
# whose cell count differs from the table column count (merged cells show up here).
# Exit code: 0 = ok, 1 = file problem, 2 = inconsistent table(s) found.
# ASCII-only on purpose (PowerShell 5.1 source-encoding safety).

param(
    [Parameter(Mandatory = $true)][string]$Docx
)

$ErrorActionPreference = 'Stop'

$Docx = [IO.Path]::GetFullPath($Docx)
if (-not (Test-Path -LiteralPath $Docx -PathType Leaf)) { throw "docx not found: $Docx" }

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $word.Documents.Open($Docx, $false, $true)

$paras = $doc.Paragraphs.Count
$tblCount = $doc.Tables.Count
$inconsistent = 0
$report = @()

for ($i = 1; $i -le $tblCount; $i++) {
    $tbl = $doc.Tables.Item($i)
    $cols = $tbl.Columns.Count
    $rowCount = $tbl.Rows.Count
    $badRows = 0
    for ($r = 1; $r -le $rowCount; $r++) {
        $cells = -1
        try { $cells = $tbl.Rows.Item($r).Cells.Count } catch { $cells = -1 }
        if ($cells -ne $cols) { $badRows++ }
    }
    if ($badRows -gt 0) { $inconsistent++ }
    $report += ('table {0}: rows={1} cols={2} rowsWithCellCountMismatch={3}' -f $i, $rowCount, $cols, $badRows)
}

$doc.Close(0)
$word.Quit()
[void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc)
[void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)

Write-Host ('file: {0}' -f $Docx)
Write-Host ('size: {0} bytes' -f (Get-Item -LiteralPath $Docx).Length)
Write-Host ('paragraphs={0} tables={1} inconsistentTables={2}' -f $paras, $tblCount, $inconsistent)
foreach ($line in $report) { Write-Host $line }

if ($inconsistent -gt 0) { exit 2 }
exit 0
