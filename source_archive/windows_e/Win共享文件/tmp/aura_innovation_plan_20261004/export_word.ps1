param([string]$SourcePath, [string]$PdfPath)
$ErrorActionPreference = 'Stop'
$wordApp = $null
$wordDoc = $null
try {
    $wordApp = New-Object -ComObject Word.Application
    $wordApp.Visible = $false
    $wordApp.DisplayAlerts = 0
    $wordApp.AutomationSecurity = 3
    $wordDoc = $wordApp.Documents.Open($SourcePath, $false, $true, $false)
    $wordDoc.Fields.Update() | Out-Null
    $wordDoc.Repaginate()
    $pageCount = $wordDoc.ComputeStatistics(2)
    $wordDoc.ExportAsFixedFormat($PdfPath, 17)
    Write-Output "Word PDF pages: $pageCount"
}
finally {
    if ($wordDoc) {
        $wordDoc.Close(0)
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordDoc)
    }
    if ($wordApp) {
        $wordApp.Quit()
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordApp)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

