param([Parameter(Mandatory=$true)][string]$ExpectedGateSha256)
$ErrorActionPreference='Stop'
$gatePath=Join-Path $PSScriptRoot 'fresh_model_removal_gate.json'
if((Get-FileHash -LiteralPath $gatePath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedGateSha256){throw 'Fresh gate fingerprint mismatch'}
$gate=Get-Content -LiteralPath $gatePath -Raw -Encoding utf8 | ConvertFrom-Json
if($gate.status -ne 'FRESH_PRODUCTION_UPLOADER_DISABLED' -or -not $gate.all_source_pins_match -or $gate.source_pins -ne 286 -or $gate.observer.enabled -ne $false -or $gate.observer.image_upload_enabled -ne $false){throw 'Actual uploader retirement is not proved'}
$gateAge=([DateTimeOffset]::UtcNow-[DateTimeOffset]::Parse($gate.checked_utc)).TotalSeconds
if($gateAge -lt 0 -or $gateAge -gt 180){throw 'Recheck the actual board before removal'}
if(@(Get-NetTCPConnection -State Listen -LocalPort 8810 -ErrorAction SilentlyContinue).Count -ne 0){throw 'Visual model listener remains'}
$modelRoot='D:\AIModels\qwen3-vl-2b-interaction'
$scanPattern=[regex]::Escape($modelRoot)+'|Qwen3VL-2B-Instruct-(Q4_K_M|Q8_0)\.gguf'
$usingModel=@(Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -and $_.CommandLine -match $scanPattern})
if($usingModel.Count -ne 0){throw 'A process still references the removed visual model'}
$protectedPorts=@(Get-NetTCPConnection -State Listen -LocalPort 11434,11435,8796,8797 -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,OwningProcess | Sort-Object LocalPort,LocalAddress)
$expected=@('manifest.json','mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf','Qwen3VL-2B-Instruct-Q4_K_M.gguf')
$directory=Get-Item -LiteralPath $modelRoot -Force
$modelParent=Get-Item -LiteralPath 'D:\AIModels' -Force
if($directory.FullName -cne $modelRoot -or -not $directory.PSIsContainer -or ($directory.Attributes -band [IO.FileAttributes]::ReparsePoint) -or ($modelParent.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Explicit regular D-drive target required'}
$items=@(Get-ChildItem -LiteralPath $modelRoot -Force)
if(@(Compare-Object ($expected|Sort-Object) ($items.Name|Sort-Object)).Count -ne 0){throw 'Unexpected files; deletion scope must not expand'}
$manifest=Get-Content -LiteralPath (Join-Path $modelRoot 'manifest.json') -Raw -Encoding utf8 | ConvertFrom-Json
$removed=@()
foreach($name in $expected){
    $target=Join-Path $modelRoot $name
    $item=Get-Item -LiteralPath $target -Force
    if($item.PSIsContainer -or $item.DirectoryName -cne $modelRoot -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Expected a regular scoped file'}
    if($name -ne 'manifest.json'){
        $entry=$manifest.files.PSObject.Properties[$name].Value
        if(-not $entry -or $entry.path -cne $target -or $entry.bytes -ne $item.Length){throw 'Original model manifest scope mismatch'}
    }
    $handle=[IO.File]::Open($target,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::None)
    $handle.Dispose()
    $removed+=[pscustomobject]@{name=$name;bytes=$item.Length}
}
foreach($item in $removed){Remove-Item -LiteralPath (Join-Path $modelRoot $item.name) -Force -ErrorAction Stop}
# The target was verified above; this only removes the now-empty directory.
Remove-Item -LiteralPath $modelRoot -ErrorAction Stop
$after=@(Get-NetTCPConnection -State Listen -LocalPort 11434,11435,8796,8797 -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,OwningProcess | Sort-Object LocalPort,LocalAddress)
$report=[ordered]@{status='REMOVED';checked_utc=[DateTime]::UtcNow.ToString('o');directory=$modelRoot;files=$removed;bytes=($removed|Measure-Object bytes -Sum).Sum;fresh_board_gate_sha256=$ExpectedGateSha256;protected_listener_owners_unchanged=(($protectedPorts|ConvertTo-Json -Compress) -ceq ($after|ConvertTo-Json -Compress));protected_listener_owners=$after;other_model_directories_touched=$false;weights_backed_up_to_shared_tree=$false;directory_absent=(-not (Test-Path -LiteralPath $modelRoot))}
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'model_removal.json') -Encoding utf8
$report | ConvertTo-Json -Depth 5 -Compress
