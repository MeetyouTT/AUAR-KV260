$ErrorActionPreference='Stop'
$python='D:\AURARuntimes\voice-py310\Scripts\python.exe'
$lan='E:\Win共享文件\语音共享文件\deliverables\2026-11-02_5090_deployment\parallel_lan'
$savedConsoleEncoding=[Console]::OutputEncoding
$savedOutputEncoding=$OutputEncoding
$report=[ordered]@{
    schema='aura-firewall-stdout-capture-reproduction-1'
    utc=[DateTime]::UtcNow.ToString('o')
    powershell_version=$PSVersionTable.PSVersion.ToString()
    initial_console_output_codepage=$savedConsoleEncoding.CodePage
    initial_pipeline_output_codepage=$savedOutputEncoding.CodePage
    model_control_performed=$false
    inference_sent=$false
    firewall_modified=$false
    board_contacted=$false
}
try {
    $raw=(& $python -B -X utf8 (Join-Path $lan 'lan_control.py') firewall-guard --expected-session '2f3a707efa62401d81fc20ef22a379cb' | Out-String)
    $report.live_guard_exit=$LASTEXITCODE
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'native_default_guard_stdout.txt'),$raw,[Text.UTF8Encoding]::new($false))
    try {
        $guard=$raw|ConvertFrom-Json
        $report.native_default_guard_parse='PASS'
        $report.native_default_alias=$guard.adapter.alias
        $report.native_default_status=$guard.status
    } catch {
        $report.native_default_guard_parse='FAILED'
        $report.native_default_guard_error=$_.Exception.Message
    }
    $cases=@()
    foreach($codepage in @(65001,936)) {
        foreach($mode in @('unicode','ascii')) {
            [Console]::OutputEncoding=[Text.Encoding]::GetEncoding($codepage)
            $raw=(& $python -B -X utf8 (Join-Path $PSScriptRoot 'capture_stdout_probe.py') $mode | Out-String)
            $item=[ordered]@{console_output_codepage=$codepage;serialization=$mode;exit=$LASTEXITCODE}
            [IO.File]::WriteAllText((Join-Path $PSScriptRoot ('synthetic_'+$codepage+'_'+$mode+'_stdout.txt')),$raw,[Text.UTF8Encoding]::new($false))
            try {
                $value=$raw|ConvertFrom-Json
                $item.parse='PASS'
                $item.alias_exact=($value.adapter.alias -ceq ([string][char]0x4ee5+[char]0x592a+[char]0x7f51))
                $item.sentinel_exact=($value.sentinel -ceq 'after_alias')
                $item.alias=$value.adapter.alias
            } catch {
                $item.parse='FAILED'
                $item.error=$_.Exception.Message
            }
            $cases+=[pscustomobject]$item
        }
    }
    $report.synthetic_cases=$cases
} finally {
    [Console]::OutputEncoding=$savedConsoleEncoding
    $OutputEncoding=$savedOutputEncoding
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'capture_reproduction.json'),($report|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
}
$report|ConvertTo-Json -Depth 8
