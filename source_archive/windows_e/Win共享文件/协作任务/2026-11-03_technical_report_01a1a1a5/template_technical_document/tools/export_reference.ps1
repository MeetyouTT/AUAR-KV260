$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$app=$null;$document=$null
try {
 $app=New-Object -ComObject Word.Application
 $app.Visible=$false;$app.DisplayAlerts=0;$app.AutomationSecurity=3
 $document=$app.Documents.Open('C:\Users\REVO1\Downloads\技术文档模板.docx',$false,$true,$false)
 $document.ExportAsFixedFormat((Join-Path $root 'qa\template_reference.pdf'),17)
 [ordered]@{pages=$document.ComputeStatistics(2);engine='Microsoft Word native PDF export';read_only=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'qa\reference_export.json') -Encoding utf8
} finally {
 if($null -ne $document){$document.Close($false);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($document)}
 if($null -ne $app){$app.Quit();[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($app)}
}
