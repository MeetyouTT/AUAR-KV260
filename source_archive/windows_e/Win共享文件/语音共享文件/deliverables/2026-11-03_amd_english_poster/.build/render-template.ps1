$taskBuild='E:\Win共享文件\语音共享文件\deliverables\2026-11-03_amd_english_poster\.build'
$alreadyRunning=@(Get-Process -Name POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$powerpoint=$null
$deck=$null
try {
  $powerpoint=New-Object -ComObject PowerPoint.Application
  $deck=$powerpoint.Presentations.Open((Join-Path $taskBuild 'template-original.pptx'),-1,0,0)
  $deck.Slides.Item(1).Export((Join-Path $taskBuild 'template-powerpoint.png'),'PNG',1920,1080)
  $deck.Close()
  $deck=$null
  Write-Output 'Source template rendered in PowerPoint without changing the original.'
} finally {
  if ($deck) { $deck.Close() }
  if ($powerpoint -and -not $alreadyRunning) { $powerpoint.Quit() }
  if ($powerpoint) { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($powerpoint) }
}
