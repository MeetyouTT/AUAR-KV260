param([string]$Py,[string]$Script,[string]$ArgLine,[string]$Out)
$ErrorActionPreference = 'Continue'
Set-Content -LiteralPath $Out -Value ("START " + (Get-Date -Format s)) -Encoding UTF8
& $Py -B -u $Script @($ArgLine -split ' ') *>&1 | Add-Content -LiteralPath $Out -Encoding UTF8
Add-Content -LiteralPath $Out -Value ("RC=" + $LASTEXITCODE) -Encoding UTF8
Add-Content -LiteralPath $Out -Value ("END " + (Get-Date -Format s)) -Encoding UTF8
