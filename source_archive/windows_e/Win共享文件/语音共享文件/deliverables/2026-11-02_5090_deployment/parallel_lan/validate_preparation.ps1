$ErrorActionPreference='Stop'
$paths=@(
    (Join-Path (Split-Path -Parent $PSScriptRoot) 'configure_model_firewall.ps1'),
    (Join-Path $PSScriptRoot 'firewall_scope.ps1'),
    (Join-Path $PSScriptRoot 'test_firewall_scope.ps1'),
    $PSCommandPath
)
$result=@(foreach($scriptPath in $paths) {
    $tokens=$null;$parseErrors=$null
    [void][Management.Automation.Language.Parser]::ParseFile($scriptPath,[ref]$tokens,[ref]$parseErrors)
    [pscustomobject]@{path=$scriptPath;parse_errors=@($parseErrors|ForEach-Object{$_.Message})}
})
$report=[ordered]@{powershell_version=$PSVersionTable.PSVersion.ToString();files=$result}
$report|ConvertTo-Json -Depth 6|Set-Content -LiteralPath (Join-Path $PSScriptRoot 'powershell_syntax.json') -Encoding utf8
if(@($result|Where-Object{$_.parse_errors.Count -gt 0}).Count){throw 'PowerShell parsing failed'}
& (Join-Path $PSScriptRoot 'test_firewall_scope.ps1') *> (Join-Path $PSScriptRoot 'firewall_scope_tests.log')
$python='D:\AURARuntimes\voice-py310\Scripts\python.exe'
& $python -B -X utf8 (Join-Path $PSScriptRoot 'test_lan_control.py') *> (Join-Path $PSScriptRoot 'python_tests.log')
if($LASTEXITCODE -ne 0){throw 'Isolated Python tests failed; logs retained'}
[ordered]@{status='PREPARATION_CHECKS_PASS';powershell_version=$PSVersionTable.PSVersion.ToString();service_started_or_stopped=$false;firewall_cmdlets_called=$false;board_contacted=$false}|ConvertTo-Json
