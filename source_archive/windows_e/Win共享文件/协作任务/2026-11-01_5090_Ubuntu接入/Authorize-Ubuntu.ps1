$ErrorActionPreference = 'Stop'
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$Host.UI.RawUI.WindowTitle = 'Ubuntu SSH key authorization - ghmd@192.168.137.117'
$publicKeyPath = Join-Path $env:USERPROFILE '.ssh\aura_5090_ubuntu_ed25519.pub'
$publicKey = (Get-Content -LiteralPath $publicKeyPath -Raw -Encoding UTF8).Trim()
$publicKeyEncoded = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($publicKey))
$installer = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'authorize_public_key.py') -Raw -Encoding UTF8
$statusPath = Join-Path $PSScriptRoot 'authorization_terminal_status.json'
@{status='WAITING_FOR_USER_PASSWORD'; started_at_utc=[DateTime]::UtcNow.ToString('o'); password_logged=$false} | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
Write-Host 'Verified Ubuntu: ghmd@192.168.137.117, via Windows hotspot 192.168.137.1'
Write-Host 'Host fingerprint: SHA256:tNZ7GjGBvS/wQDcvA2omrWvQAKLYIaR4/a2WaBf/Mrs'
Write-Host 'Enter the Ubuntu ghmd login password at the SSH prompt. Input stays invisible.'
Write-Host 'This authorizes the new 5090 public key and preserves all existing keys.'
Write-Host ''
try {
    $output = $installer | & "$env:WINDIR\System32\OpenSSH\ssh.exe" -T -o BatchMode=no -o PubkeyAuthentication=no -o PreferredAuthentications=password -o NumberOfPasswordPrompts=3 -o StrictHostKeyChecking=yes aura-ubuntu python3 - --public-key-base64 $publicKeyEncoded --apply
    $resultCode = $LASTEXITCODE
    $output | Tee-Object -FilePath (Join-Path $PSScriptRoot 'authorization_result.json') | Write-Host
    @{status=$(if($resultCode -eq 0){'AUTHORIZATION_COMPLETED'}else{'AUTHORIZATION_FAILED'}); exit_code=$resultCode; finished_at_utc=[DateTime]::UtcNow.ToString('o'); password_logged=$false} | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
    if ($resultCode -eq 0) { Write-Host 'Success. Return to the chat; Codex will verify key-only SSH.' -ForegroundColor Green }
    else { Write-Host 'SSH authorization did not complete. Return to the chat with the visible error, without the password.' -ForegroundColor Yellow }
} catch {
    @{status='LOCAL_SCRIPT_ERROR'; error=$_.Exception.Message; finished_at_utc=[DateTime]::UtcNow.ToString('o'); password_logged=$false} | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
    Write-Host $_.Exception.Message -ForegroundColor Red
}
