$ErrorActionPreference='Stop'
$ready=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'services_ready.json') -Raw -Encoding utf8 | ConvertFrom-Json
$board=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'board_deployment.json') -Raw -Encoding utf8 | ConvertFrom-Json
if ($ready.status -ne 'READY' -or $board.status -ne 'COMMITTED') {throw 'Deployment gates not complete'}
if (@(Get-NetTCPConnection -State Listen -LocalPort 8810 -ErrorAction SilentlyContinue).Count -ne 0) {throw 'Visual model listener remains'}
$modelRoot='D:\AIModels\qwen3-vl-2b-interaction'
$expected=@('manifest.json','mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf','Qwen3VL-2B-Instruct-Q4_K_M.gguf')
$directory=Get-Item -LiteralPath $modelRoot -Force
if ($directory.FullName -cne $modelRoot -or -not $directory.PSIsContainer -or ($directory.Attributes -band [IO.FileAttributes]::ReparsePoint)) {throw 'Model directory scope mismatch'}
$items=@(Get-ChildItem -LiteralPath $modelRoot -Force)
if (@(Compare-Object ($expected | Sort-Object) ($items.Name | Sort-Object)).Count -ne 0) {throw 'Unexpected files; do not broaden deletion'}
$removed=@()
foreach($name in $expected) {
    $target=Join-Path $modelRoot $name
    $item=Get-Item -LiteralPath $target -Force
    if ($item.PSIsContainer -or $item.DirectoryName -cne $modelRoot -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {throw 'Expected a regular scoped model file'}
    $removed+=[pscustomobject]@{name=$name;bytes=$item.Length}
}
foreach($item in $removed) {Remove-Item -LiteralPath (Join-Path $modelRoot $item.name) -Force -ErrorAction Stop}
# This is an empty-directory removal, never a recursive deletion.
Remove-Item -LiteralPath $modelRoot -ErrorAction Stop
$report=[ordered]@{status='REMOVED';directory=$modelRoot;files=$removed;bytes=($removed | Measure-Object bytes -Sum).Sum;other_model_directories_touched=$false;weights_backed_up_to_shared_tree=$false}
$report | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'model_removal.json') -Encoding utf8
$report | ConvertTo-Json -Depth 4 -Compress
