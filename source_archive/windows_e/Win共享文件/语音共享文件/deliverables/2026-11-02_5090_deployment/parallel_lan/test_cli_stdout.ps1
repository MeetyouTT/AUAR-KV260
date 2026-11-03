# Isolated real-CLI stdout regression. No model, firewall or board operations.
$ErrorActionPreference='Stop'
$python='D:\AURARuntimes\voice-py310\Scripts\python.exe'
$savedEncoding=[Console]::OutputEncoding
$expectedAlias=[string][char]0x4ee5+[char]0x592a+[char]0x7f51
$expectedLabel=[string][char]0x96ea+[char]0x5983
$cases=@()
try {
    foreach($codepage in @(65001,936,437)) {
        [Console]::OutputEncoding=[Text.Encoding]::GetEncoding($codepage)
        $raw=(& $python -B -X utf8 (Join-Path $PSScriptRoot 'cli_stdout_fixture.py') | Out-String)
        if($LASTEXITCODE -ne 0){throw 'Isolated real CLI fixture failed'}
        if(@($raw.ToCharArray()|Where-Object{[int]$_ -gt 127}).Count){throw 'CLI stdout is not ASCII JSON'}
        $parsed=$raw|ConvertFrom-Json
        if($parsed -is [Array]){throw 'CLI stdout contains multiple JSON values'}
        if($parsed.status -cne 'FRESH_IDLE_MODEL_OWNER_CONFIRMED' -or
           $parsed.session_id -cne ('a'*32) -or
           $parsed.adapter.alias -cne $expectedAlias -or
           $parsed.health.label -cne $expectedLabel){throw 'CLI JSON metadata or exact Unicode changed'}
        $cases+=[pscustomobject]@{console_output_codepage=$codepage;ascii_json=$true;exact_unicode_alias=$true;exact_unicode_nested_label=$true;status='PASS'}
    }
} finally {
    [Console]::OutputEncoding=$savedEncoding
}
[ordered]@{schema='aura-lan-cli-stdout-regression-1';status='PASS';powershell_version=$PSVersionTable.PSVersion.ToString();cases=$cases;model_control_performed=$false;inference_sent=$false;firewall_modified=$false;board_contacted=$false}|ConvertTo-Json -Depth 6
