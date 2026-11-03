#Requires -Version 5.1
<#
  build_aura_repo.ps1
  Stage the reusable assets of the upstream "wujing-lite" project into the new AURA repo
  (Kria KV260) according to D5 section 19.2 directory blueprint.
  Usage:
    powershell -NoProfile -ExecutionPolicy Bypass -File tools\build_aura_repo.ps1 -Source <wujing-lite> -Dest <aura> -Check
    powershell -NoProfile -ExecutionPolicy Bypass -File tools\build_aura_repo.ps1 -Source <wujing-lite> -Dest <aura> -Apply [-IncludeHeavy]
  Notes: paths are arguments because Windows PowerShell 5.1 reads a non-BOM .ps1 as ANSI,
         so no non-ASCII literal may appear in this file.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Source,
  [Parameter(Mandatory=$true)][string]$Dest,
  [switch]$Check,
  [switch]$Apply,
  [switch]$IncludeHeavy
)
$ErrorActionPreference = 'Stop'
if (-not $Check -and -not $Apply) { throw 'Specify -Check (dry run) or -Apply (copy).' }
if (-not (Test-Path -LiteralPath $Source)) { throw ('Source not found: ' + $Source) }

$map = @(
  [pscustomobject]@{ Src='board\runtime'; Dst='board\runtime';     Heavy=$false; Note='runtime core: event bus / fsm / validator / adapter / mocks / logging' },
  [pscustomobject]@{ Src='board\ui';      Dst='board\interaction'; Heavy=$false; Note='avatar + ui code, lvgl assets table, pc prototypes' },
  [pscustomobject]@{ Src='ui_spec';       Dst='ui';                Heavy=$false; Note='ui_state.schema.json / avatar_board_manifest.json / layout / tokens' },
  [pscustomobject]@{ Src='schemas';       Dst='common\schemas';    Heavy=$false; Note='dialogue_request / dialogue_response / scene_state' },
  [pscustomobject]@{ Src='tests';         Dst='tests';             Heavy=$false; Note='pytest suite (436 passed baseline)' },
  [pscustomobject]@{ Src='tools';         Dst='scripts';           Heavy=$false; Note='export and validation tools' },
  [pscustomobject]@{ Src='docs';          Dst='docs';              Heavy=$false; Note='technical records (md + docx pairs)' },
  [pscustomobject]@{ Src='assets\avatar'; Dst='ui\assets\avatar';  Heavy=$true;  Note='avatar frame streams (rgb565)' },
  [pscustomobject]@{ Src='models';        Dst='models';            Heavy=$true;  Note='onnx model artifacts' }
)

$skipDirName = @('__pycache__', '.pytest_cache', '.git')
$skipExt = @('.pyc')

function Test-Skip([System.IO.FileInfo]$f) {
  foreach ($d in $skipDirName) { if ($f.FullName -match ('\\' + [regex]::Escape($d) + '\\')) { return $true } }
  return ($skipExt -contains $f.Extension.ToLower())
}

$plan = New-Object System.Collections.ArrayList
foreach ($m in $map) {
  $srcRoot = Join-Path $Source $m.Src
  if (-not (Test-Path -LiteralPath $srcRoot)) {
    [void]$plan.Add([pscustomobject]@{ Src=$srcRoot; Dst=''; Bytes=0; State='MISSING'; Note=$m.Note })
    continue
  }
  $base = (Get-Item -LiteralPath $srcRoot).FullName
  $files = @(Get-ChildItem -LiteralPath $srcRoot -Recurse -File -Force | Where-Object { -not (Test-Skip $_) })
  foreach ($f in $files) {
    $rel = $f.FullName.Substring($base.Length).TrimStart('\')
    $dstPath = Join-Path (Join-Path $Dest $m.Dst) $rel
    $state = 'PLAN'
    if ($m.Heavy -and -not $IncludeHeavy) { $state = 'SKIP_HEAVY' }
    elseif (Test-Path -LiteralPath $dstPath) { $state = 'OVERWRITE' }
    [void]$plan.Add([pscustomobject]@{ Src=$f.FullName; Dst=$dstPath; Bytes=$f.Length; State=$state; Note=$m.Note })
  }
}

$ok = @($plan | Where-Object { $_.State -eq 'PLAN' -or $_.State -eq 'OVERWRITE' })
$sum = ($ok | Measure-Object -Property Bytes -Sum).Sum
Write-Output ('MODE       = ' + $(if ($Apply) { 'APPLY' } else { 'CHECK (dry run)' }))
Write-Output ('SCOPE      = ' + $(if ($IncludeHeavy) { 'code + heavy assets' } else { 'code only (heavy assets skipped)' }))
Write-Output ('PLANNED    = ' + $ok.Count + ' files, ' + $sum + ' bytes')
Write-Output ('SKIP_HEAVY = ' + @($plan | Where-Object { $_.State -eq 'SKIP_HEAVY' }).Count + ' files')
Write-Output ('MISSING    = ' + @($plan | Where-Object { $_.State -eq 'MISSING' }).Count)
Write-Output ('OVERWRITE  = ' + @($plan | Where-Object { $_.State -eq 'OVERWRITE' }).Count)
foreach ($g in ($ok | Group-Object Note)) {
  $gs = ($g.Group | Measure-Object -Property Bytes -Sum).Sum
  Write-Output ('  - ' + $g.Name.PadRight(62) + ' n=' + $g.Count.ToString().PadLeft(4) + ' bytes=' + $gs)
}
foreach ($mi in ($plan | Where-Object { $_.State -eq 'MISSING' })) { Write-Output ('  ! MISSING: ' + $mi.Src) }

if (-not $Apply) { Write-Output 'CHECK ONLY - nothing was written.'; return }

$manifest = New-Object System.Collections.ArrayList
foreach ($p in $ok) {
  $dir = Split-Path -Parent $p.Dst
  if (-not (Test-Path -LiteralPath $dir)) { [void](New-Item -ItemType Directory -Path $dir -Force) }
  Copy-Item -LiteralPath $p.Src -Destination $p.Dst -Force
  $h = (Get-FileHash -LiteralPath $p.Dst -Algorithm SHA256).Hash
  [void]$manifest.Add($h + "`t" + $p.Bytes + "`t" + $p.Dst)
}
$manPath = Join-Path (Split-Path -Parent $Dest) 'tools\_aura_import_manifest.tsv'
$manifest | Set-Content -LiteralPath $manPath -Encoding UTF8
Write-Output ('APPLIED    = ' + $ok.Count + ' files')
Write-Output ('MANIFEST   = ' + $manPath)
