$ErrorActionPreference='Stop'
$python='D:\AURARuntimes\voice-py310\Scripts\python.exe'
$lan='E:\Win共享文件\语音共享文件\deliverables\2026-11-02_5090_deployment\parallel_lan'
$savedEncoding=[Console]::OutputEncoding
$report=[ordered]@{schema='aura-firewall-full-guard-cp936-reproduction-1';utc=[DateTime]::UtcNow.ToString('o');powershell_version=$PSVersionTable.PSVersion.ToString();model_control_performed=$false;inference_sent=$false;firewall_modified=$false;board_contacted=$false}
try {
    [Console]::OutputEncoding=[Text.Encoding]::GetEncoding(936)
    $raw=(& $python -B -X utf8 (Join-Path $lan 'lan_control.py') firewall-guard --expected-session '2f3a707efa62401d81fc20ef22a379cb' | Out-String)
    $report.exit=$LASTEXITCODE
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'full_cp936_guard_stdout_before.txt'),$raw,[Text.UTF8Encoding]::new($false))
    try {
        $guard=$raw|ConvertFrom-Json
        $report.parse='PASS'
        $report.alias=$guard.adapter.alias
        $report.status=$guard.status
    } catch {
        $report.parse='FAILED'
        $report.error=$_.Exception.Message
    }
} finally {
    [Console]::OutputEncoding=$savedEncoding
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'full_cp936_guard_before.json'),($report|ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
}
$report|ConvertTo-Json -Depth 5
