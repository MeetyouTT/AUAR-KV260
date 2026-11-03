$ErrorActionPreference='Stop'
$lan='E:\Win共享文件\语音共享文件\deliverables\2026-11-02_5090_deployment\parallel_lan'
$paths=@((Join-Path (Split-Path -Parent $lan) 'configure_model_firewall.ps1'),(Join-Path $lan 'firewall_scope.ps1'),(Join-Path $lan 'test_firewall_scope.ps1'),(Join-Path $lan 'validate_preparation.ps1'),(Join-Path $lan 'test_cli_stdout.ps1'))
$parsed=@(foreach($path in $paths){
    $tokens=$null;$parseErrors=$null
    [void][Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$parseErrors)
    [pscustomobject]@{path=$path;errors=@($parseErrors|ForEach-Object{$_.Message})}
})
if(@($parsed|Where-Object{$_.errors.Count}).Count){throw 'PowerShell parsing failed'}
$result=[ordered]@{status='PASS';powershell_version=$PSVersionTable.PSVersion.ToString();files=$parsed}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'powershell_syntax_ps51_after.json'),($result|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
[ordered]@{status='PASS';powershell_version=$PSVersionTable.PSVersion.ToString();parse_errors=0;files=$parsed.Count}|ConvertTo-Json
