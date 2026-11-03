$ErrorActionPreference='Stop'
$Host.UI.RawUI.WindowTitle='AURA KV260 - authorize this computer'
$root=$PSScriptRoot
$ssh=Join-Path $env:SystemRoot 'System32\OpenSSH\ssh.exe'
$script=Join-Path $root 'authorize_this_host_on_board.sh'
$encoded=[Convert]::ToBase64String([IO.File]::ReadAllBytes($script))
$remoteCommand="printf '%s' '$encoded' | base64 -d | sh"
Write-Host '请在此终端输入 KV260 的 root 密码；输入时不会显示字符。' -ForegroundColor Cyan
Write-Host '本次操作仅追加本机公钥，保留已有授权，并验证新的公钥登录。'
& $ssh -b 192.168.50.1 -o ConnectTimeout=10 -o ConnectionAttempts=1 -o StrictHostKeyChecking=yes -o UpdateHostKeys=no -o BatchMode=no -o PubkeyAuthentication=no -o PreferredAuthentications=password -o NumberOfPasswordPrompts=3 aura-kv260 $remoteCommand
$authorizationCode=$LASTEXITCODE
$result=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');status='PASSWORD_AUTHORIZATION_FAILED';authorization_exit_code=$authorizationCode;new_key_authenticated=$false;password_stored=$false;motion_performed=$false}
if($authorizationCode -eq 0){
    $boot=& $ssh -b 192.168.50.1 -o ConnectTimeout=8 -o ConnectionAttempts=1 -o BatchMode=yes -o StrictHostKeyChecking=yes -o UpdateHostKeys=no -o PreferredAuthentications=publickey aura-kv260 'cat /proc/sys/kernel/random/boot_id'
    $result.public_key_probe_exit_code=$LASTEXITCODE
    if($LASTEXITCODE -eq 0){
        $result.status='PUBLIC_KEY_AUTHORIZED_AND_VERIFIED'
        $result.new_key_authenticated=$true
        $result.board_boot_id=([string]$boot).Trim()
    }else{$result.status='PUBLIC_KEY_AUTHORIZATION_NEEDS_REVIEW'}
}
$result|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $root 'interactive_authorization_result.json') -Encoding utf8
$result|ConvertTo-Json
Write-Host '结果已记录。可以关闭此终端窗口。' -ForegroundColor Cyan
