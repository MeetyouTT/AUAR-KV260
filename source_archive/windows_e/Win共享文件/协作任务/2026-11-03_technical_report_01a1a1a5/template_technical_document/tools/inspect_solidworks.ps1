$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$app=New-Object -ComObject SldWorks.Application.30
$report=[ordered]@{revision=$app.RevisionNumber();opened_before=$app.GetDocumentCount();active_before=$null}
if($null -ne $app.ActiveDoc){$report.active_before=$app.ActiveDoc.GetPathName()}
$err=0;$warn=0
$file=Join-Path $root 'cad\source\together.SLDASM'
$doc=$app.OpenDoc6($file,2,3,'',[ref]$err,[ref]$warn)
$report.open_error=$err;$report.open_warning=$warn
if($null -eq $doc){$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $root 'qa\solidworks_open.json') -Encoding utf8;throw 'SolidWorks returned no assembly document'}
$report.title=$doc.GetTitle();$report.path=$doc.GetPathName();$report.type=$doc.GetType();$report.save_flag=$doc.GetSaveFlag()
try{$report.box_m=$doc.GetBox(0)}catch{$report.box_error=$_.Exception.Message}
$components=@()
foreach($comp in $doc.GetComponents($false)) {
 $c=[ordered]@{name=$comp.Name2;path=$comp.GetPathName();suppression=$comp.GetSuppression()}
 try{$c.box_m=$comp.GetBox($false,$false)}catch{$c.box_error=$_.Exception.Message}
 $components+=$c
}
$report.components=$components
$views=@([ordered]@{name='assembly_isometric';view='*Isometric';id=7},[ordered]@{name='assembly_front';view='*Front';id=1},[ordered]@{name='assembly_back';view='*Back';id=2},[ordered]@{name='assembly_side';view='*Right';id=4})
$results=@()
foreach($v in $views){
 $doc.ShowNamedView2($v.view,$v.id)
 $doc.ViewZoomtofit2()
 $target=Join-Path $root ('figures\'+$v.name+'.bmp')
 $ok=$doc.SaveBMP($target,1600,1200)
 $results+=[ordered]@{name=$v.name;success=$ok;exists=(Test-Path -LiteralPath $target)}
}
$report.views=$results
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $root 'qa\solidworks_open.json') -Encoding utf8
$report | ConvertTo-Json -Depth 8
