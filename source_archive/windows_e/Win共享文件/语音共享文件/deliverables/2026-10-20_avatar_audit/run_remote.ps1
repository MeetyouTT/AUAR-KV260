param([Parameter(Mandatory=$true)][string]$Script, [Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference='Stop'
$probeText=Get-Content -LiteralPath $Script -Raw -Encoding utf8
$probeOutput=$probeText | & C:/Windows/System32/OpenSSH/ssh.exe -i C:/Users/35870/.codex/visualizations/2026/10/09/01a12110-3ba4-7651-b3d7-2e6560916eb6/board-access-20261018/id_ed25519 -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=4 root@192.168.50.2 'python3 -B -'
if ($LASTEXITCODE -ne 0) {throw 'Remote script failed'}
$probeOutput | Set-Content -LiteralPath $Output -Encoding utf8
$probeOutput
