$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms.DataVisualization
Add-Type -AssemblyName System.Drawing
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$figDir = Join-Path $base 'figures'
[void][IO.Directory]::CreateDirectory($figDir)
$voice = Get-Content -LiteralPath (Join-Path $base 'RESULTS.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$dpu = Get-Content -LiteralPath (Join-Path $base 'DPU_LOCAL_CROSSCHECK.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$llm = @(Import-Csv -LiteralPath (Join-Path $base 'llm_cases.csv') -Encoding UTF8)
$tts = @(Import-Csv -LiteralPath (Join-Path $base 'tts_cases.csv') -Encoding UTF8)
$font = New-Object Drawing.Font('Microsoft YaHei', 13)
$titleFont = New-Object Drawing.Font('Microsoft YaHei', 22, [Drawing.FontStyle]::Bold)
$blue = [Drawing.Color]::FromArgb(31, 96, 166)
$green = [Drawing.Color]::FromArgb(34, 139, 119)
$orange = [Drawing.Color]::FromArgb(223, 139, 42)

function New-Chart($title) {
    $c = New-Object Windows.Forms.DataVisualization.Charting.Chart
    $c.Width = 1600; $c.Height = 1120; $c.BackColor = [Drawing.Color]::White
    $c.AntiAliasing = 'All'; $c.TextAntiAliasingQuality = 'High'
    $t = $c.Titles.Add($title); $t.Font = $titleFont
    return ,$c
}
function Add-Area($c, $name, $y, $ylabel, $maximum) {
    $a = New-Object Windows.Forms.DataVisualization.Charting.ChartArea($name)
    $a.Position = New-Object Windows.Forms.DataVisualization.Charting.ElementPosition(5, $y, 90, 33)
    $a.AxisY.Minimum = 0; $a.AxisY.Maximum = $maximum; $a.AxisY.Title = $ylabel
    $a.AxisY.TitleFont = $font; $a.AxisY.LabelStyle.Font = $font
    $a.AxisX.LabelStyle.Font = $font; $a.AxisX.Interval = 1
    $a.AxisX.MajorGrid.Enabled = $false
    $a.AxisY.MajorGrid.LineColor = [Drawing.Color]::FromArgb(225, 231, 237)
    $a.AxisX.LineColor = [Drawing.Color]::Gray; $a.AxisY.LineColor = [Drawing.Color]::Gray
    $a.BackColor = [Drawing.Color]::White
    $c.ChartAreas.Add($a)
    return ,$a
}
function Add-Series($c, $name, $area, $color) {
    $s = New-Object Windows.Forms.DataVisualization.Charting.Series($name)
    $s.ChartArea = $area; $s.ChartType = 'Column'; $s.Color = $color
    $s.IsVisibleInLegend = $false; $s.IsValueShownAsLabel = $true
    $s.LabelFormat = '0.00'; $s.Font = $font; $s['PointWidth'] = '0.5'
    $c.Series.Add($s)
    return ,$s
}
function Add-Note($c, $text) {
    $t = $c.Titles.Add($text); $t.Font = New-Object Drawing.Font('Microsoft YaHei', 11)
    $t.Docking = 'Bottom'; $t.Alignment = 'MiddleLeft'
}

$c = New-Chart 'DPU视觉管线：实际运行频率与阶段耗时'
$a = Add-Area $c 'rate' 12 '实际完成／准入频率（Hz）' 12
$s = Add-Series $c 'rate' 'rate' $blue
$colors = @($blue, $green, $orange)
$i = 0
foreach ($m in $dpu.models) {
    $n = $s.Points.AddXY([string]$m.model, [double]$m.observed_rate_hz)
    $s.Points[$n].Color = $colors[$i]; $i++
}
$a = Add-Area $c 'timing' 53 '阶段窗口平均耗时（ms）' 20
$s = Add-Series $c 'stage_mean' 'timing' $green
$i = 0
foreach ($m in $dpu.models) {
    $n = $s.Points.AddXY([string]$m.model, [double]$m.window_mean_stage_ms)
    $s.Points[$n].Color = $colors[$i]; $i++
}
Add-Note $c "KV260现役管线；180.151秒／90点；原视觉持续运行，转轴停止，重叠GUI采样均为暂停监听。`n频率：窗口计数差÷179.774秒健康快照端点间隔，并非模型独占最大FPS。`nYOLO耗时含原生执行及解码；YuNet/SFace为native临界区墙钟。硬件DPU利用率未提供。"
$c.SaveImage((Join-Path $figDir '01_DPU_runtime_performance.png'), 'Png')
$c.Dispose()

$c = New-Chart '语音模型性能：公开固定输入的暖态逐例结果'
$a = Add-Area $c 'llm' 12 '27B：完整RPC（秒）' 2.6
$s = Add-Series $c 'LLM RPC' 'llm' $blue
foreach ($r in $llm) { [void]$s.Points.AddXY(('样本 ' + $r.case), [double]$r.rpc_ms / 1000) }
$first = New-Object Windows.Forms.DataVisualization.Charting.Series('First JSON content')
$first.ChartArea = 'llm'; $first.ChartType = 'Line'; $first.Color = $orange; $first.BorderWidth = 3
$first.MarkerStyle = 'Circle'; $first.MarkerSize = 11; $first.IsVisibleInLegend = $false
$first.IsValueShownAsLabel = $true; $first.LabelFormat = '0.000'; $first.Font = $font
foreach ($r in $llm) { [void]$first.Points.AddXY(('样本 ' + $r.case), [double]$r.first_content_ms / 1000) }
$c.Series.Add($first)
$a = Add-Area $c 'tts' 53 'OmniVoice16：完整RPC（秒）' 1.8
$s = Add-Series $c 'TTS RPC' 'tts' $green
foreach ($r in $tts) { [void]$s.Points.AddXY(('样本 ' + $r.case), [double]$r.rpc_ms / 1000) }
Add-Note $c "上图：蓝柱为完整RPC，橙线为首个非空JSON内容；下图：TTS完整RPC。各5例全部成功。`n27B IQ4_XS／上下文2048／think=false；解码中位40.85 token/s。TTS均非缓存；RTF中位0.128。`n计划样本4遇后台／现场业务占用，跳过且未发请求。测量不含ASR、真实记忆上下文或扬声器声学首声。"
$c.SaveImage((Join-Path $figDir '02_LLM_TTS_public_cases.png'), 'Png')
$c.Dispose()

Get-ChildItem -LiteralPath $figDir -File | Select-Object Name, Length
