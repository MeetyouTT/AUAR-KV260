param([Parameter(Mandatory=$true)][string]$InputDeck,[Parameter(Mandatory=$true)][string]$Prefix)
$ErrorActionPreference='Stop'
$hadPowerPoint=@(Get-Process -Name POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$powerpoint=$null
$deck=$null
try {
  $powerpoint=New-Object -ComObject PowerPoint.Application
  $deck=$powerpoint.Presentations.Open($InputDeck,-1,0,0)
  for($slideNo=1;$slideNo -le $deck.Slides.Count;$slideNo++) {
    $deck.Slides.Item($slideNo).Export(($Prefix+'-'+$slideNo+'.png'),'PNG',1920,1080)
  }
  [pscustomobject]@{Slides=$deck.Slides.Count; Width=$deck.PageSetup.SlideWidth; Height=$deck.PageSetup.SlideHeight; NativePowerPointRender=$true} | ConvertTo-Json -Compress
} finally {
  if($deck) {$deck.Close(); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($deck)}
  if($powerpoint) {
    if(-not $hadPowerPoint){$powerpoint.Quit()}
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($powerpoint)
  }
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}
