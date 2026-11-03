$ErrorActionPreference = 'Stop'
$reportRoot = 'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5'
$reportDocx = Join-Path $reportRoot 'auar_xuefei_technical_report.docx'
$reportPdf = Join-Path $reportRoot 'auar_xuefei_technical_report.pdf'
$reportApp = $null
$reportDocument = $null
try {
    $reportApp = New-Object -ComObject Word.Application
    $reportApp.Visible = $false
    $reportApp.DisplayAlerts = 0
    $reportApp.AutomationSecurity = 3
    $reportApp.Options.UpdateLinksAtOpen = $false
    $reportDocument = $reportApp.Documents.Open($reportDocx, $false, $false, $false)
    $reportDocument.Repaginate()
    $reportDocument.Fields.Update() | Out-Null
    foreach ($reportToc in $reportDocument.TablesOfContents) { $reportToc.Update() }
    foreach ($reportStyleId in @(-20, -21)) {
        $reportStyle = $reportDocument.Styles.Item($reportStyleId)
        $reportStyle.Font.Name = '宋体'
        $reportStyle.Font.NameFarEast = '宋体'
        $reportStyle.Font.Size = 10
        $reportStyle.ParagraphFormat.DisableLineHeightGrid = -1
        $reportStyle.ParagraphFormat.LineSpacingRule = 4
        $reportStyle.ParagraphFormat.LineSpacing = 13
        $reportStyle.ParagraphFormat.SpaceBefore = 0
        $reportStyle.ParagraphFormat.SpaceAfter = 2
    }
    foreach ($reportToc in $reportDocument.TablesOfContents) {
        $reportToc.Range.Font.Size = 10
        $reportToc.Range.ParagraphFormat.DisableLineHeightGrid = -1
        $reportToc.Range.ParagraphFormat.LineSpacingRule = 4
        $reportToc.Range.ParagraphFormat.LineSpacing = 13
        $reportToc.Range.ParagraphFormat.SpaceBefore = 0
        $reportToc.Range.ParagraphFormat.SpaceAfter = 2
    }
    $reportDocument.Repaginate()
    foreach ($reportToc in $reportDocument.TablesOfContents) { $reportToc.UpdatePageNumbers() }
    $reportDocument.Save()
    $reportDocument.ExportAsFixedFormat($reportPdf, 17)
    $reportPages = $reportDocument.ComputeStatistics(2)
    [ordered]@{ engine='Microsoft Word native PDF export'; pages=$reportPages; docx=$reportDocx; pdf=$reportPdf; fields_updated=$true } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $reportRoot 'qa\word_export.json') -Encoding utf8
    Write-Output ('Exported pages: ' + $reportPages)
}
finally {
    if ($null -ne $reportDocument) { $reportDocument.Close($false); [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($reportDocument) }
    if ($null -ne $reportApp) { $reportApp.Quit(); [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($reportApp) }
}
