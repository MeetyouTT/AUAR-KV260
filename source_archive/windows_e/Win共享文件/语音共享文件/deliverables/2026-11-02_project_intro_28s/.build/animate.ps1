param([switch]$Video)
$ErrorActionPreference='Stop'
$buildDir=$PSScriptRoot
$config=Get-Content -LiteralPath (Join-Path $buildDir 'timing.json') -Raw | ConvertFrom-Json
$ppt=New-Object -ComObject PowerPoint.Application
$ppt.AutomationSecurity=3
$ppt.DisplayAlerts=1
$deck=$null
try {
    $deck=$ppt.Presentations.Open((Join-Path $buildDir 'draft.pptx'),0,0,0)
    $audit=@()
    foreach($spec in $config.slides) {
        $slide=$deck.Slides.Item([int]$spec.slide)
        for($i=1;$i -le $slide.Shapes.Count;$i++) {
            $shape=$slide.Shapes.Item($i)
            if($shape.HasTextFrame -eq -1) {
                $shape.TextFrame.TextRange.Font.Name='Microsoft YaHei'
                $shape.TextFrame.TextRange.Font.NameFarEast='Microsoft YaHei'
                $shape.TextFrame2.TextRange.Font.Name='Microsoft YaHei'
                $shape.TextFrame2.TextRange.Font.NameFarEast='Microsoft YaHei'
            }
        }
        if($null -ne $spec.characterClip) {
            for($i=$slide.Shapes.Count;$i -ge 1;$i--) {
                if($slide.Shapes.Item($i).Type -eq 13) { $slide.Shapes.Item($i).Delete() }
            }
            $a=$spec.characterClip
            $imagePath=Join-Path $buildDir ('assets\'+$a.clip+'.gif')
            $pic=$slide.Shapes.AddPicture($imagePath,0,-1,([single]$a.x*0.75),([single]$a.y*0.75),([single]$a.width*0.75),([single]$a.height*0.75))
            $pic.Name='avatar_animation'
            $pic.AlternativeText='雪妃原生渲染的动画示意，非现场实屏录像'
            $pic.ZOrder(1)
        }
        foreach($entry in $spec.elements) {
            $shape=$slide.Shapes.Item([string]$entry.name)
            $effect=$slide.TimeLine.MainSequence.AddEffect($shape,[int]$entry.effect,0,2)
            $effect.Timing.Duration=[single]$entry.duration
            $effect.Timing.TriggerDelayTime=[single]$entry.at
            $effect.Timing.TriggerType=2
        }
        $slide.SlideShowTransition.EntryEffect=3849
        $slide.SlideShowTransition.Duration=[single]$config.transitionSeconds
        $slide.SlideShowTransition.AdvanceOnClick=0
        $slide.SlideShowTransition.AdvanceOnTime=-1
        $slide.SlideShowTransition.AdvanceTime=[single]$spec.seconds
        $audit+=@{slide=[int]$spec.slide;advance_s=$slide.SlideShowTransition.AdvanceTime;transition_s=$slide.SlideShowTransition.Duration;automatic_effects=$slide.TimeLine.MainSequence.Count;shape_names=@(for($i=1;$i -le $slide.Shapes.Count;$i++){$slide.Shapes.Item($i).Name})}
    }
    $deck.SlideShowSettings.AdvanceMode=2
    $deck.SlideShowSettings.ShowWithAnimation=-1
    $deck.SlideShowSettings.ShowWithNarration=0
    $deck.SlideShowSettings.LoopUntilStopped=0
    $candidate=Join-Path $buildDir 'animated_candidate.pptx'
    $deck.SaveAs($candidate,24)
    $renderDir=Join-Path $buildDir 'powerpoint-renders'
    New-Item -ItemType Directory -Force -Path $renderDir | Out-Null
    for($i=1;$i -le $deck.Slides.Count;$i++) { $deck.Slides.Item($i).Export((Join-Path $renderDir ('slide-'+$i+'.png')),'PNG',1280,720) }
    $audit | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $buildDir 'powerpoint_audit.json') -Encoding utf8
    Write-Output ('ANIMATED_CANDIDATE='+$candidate)
    if($Video) {
        $videoPath=Join-Path $buildDir 'playback_check.mp4'
        $deck.CreateVideo($videoPath,$true,4,720,30,85)
        $deadline=[DateTime]::UtcNow.AddMinutes(4)
        $lastReport=[DateTime]::UtcNow
        do {
            Start-Sleep -Milliseconds 700
            $status=[int]$deck.CreateVideoStatus
            if(([DateTime]::UtcNow-$lastReport).TotalSeconds -ge 15) { Write-Output ('VIDEO_STATUS='+$status); $lastReport=[DateTime]::UtcNow }
            if([DateTime]::UtcNow -gt $deadline) { throw 'PowerPoint video validation timed out' }
        } while($status -eq 1 -or $status -eq 2)
        Write-Output ('VIDEO_FINAL_STATUS='+$status)
        if($status -ne 3) { throw ('PowerPoint video export failed: '+$status) }
        Write-Output ('VALIDATION_VIDEO='+$videoPath)
    }
} finally {
    if($null -ne $deck) { $deck.Close() }
    if($ppt.Presentations.Count -eq 0) { $ppt.Quit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
}
