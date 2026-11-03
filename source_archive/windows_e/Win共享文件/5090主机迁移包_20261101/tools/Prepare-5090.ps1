param(
    [switch]$ApplySsh,
    [string]$UbuntuHost = '192.168.137.141',
    [string]$BoardHost = '192.168.50.2'
)
$ErrorActionPreference = 'Stop'
$migrationPackage = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent $migrationPackage
$projectRoot = Join-Path $workspaceRoot '语音共享文件'
$sshDirectory = Join-Path $env:USERPROFILE '.ssh'
$result = [ordered]@{
    mode = $(if ($ApplySsh) {'PREPARE_NEW_HOST_SSH'} else {'CHECK_ONLY'})
    package = $migrationPackage
    workspace = $workspaceRoot
    project_present = Test-Path -LiteralPath (Join-Path $projectRoot 'start_inference.ps1')
    model_storage_config_present = Test-Path -LiteralPath (Join-Path $projectRoot 'aura/config/model_storage.local.json')
    ssh_available = [bool](Get-Command ssh.exe -ErrorAction SilentlyContinue)
    python_available = [bool](Get-Command python.exe -ErrorAction SilentlyContinue)
    git_available = [bool](Get-Command git.exe -ErrorAction SilentlyContinue)
    nvidia_smi_available = [bool](Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue)
    old_private_keys_imported = $false
    services_started = $false
    device_commands_sent = $false
}
if (-not $ApplySsh) {
    $result | ConvertTo-Json -Depth 6
    return
}
if (-not $result.project_present) { throw 'Copy the complete Win共享文件 workspace, including 语音共享文件, before setup.' }
foreach ($hostAddress in @($UbuntuHost, $BoardHost)) {
    $parsedAddress = $null
    if (-not [System.Net.IPAddress]::TryParse($hostAddress, [ref]$parsedAddress)) { throw 'Pass a verified IP address.' }
}
$keygen = (Get-Command ssh-keygen.exe -ErrorAction Stop).Source
New-Item -ItemType Directory -Path $sshDirectory -Force | Out-Null
$publicDirectory = Join-Path $migrationPackage 'codex/new_host_public_keys'
New-Item -ItemType Directory -Path $publicDirectory -Force | Out-Null
foreach ($role in @('ubuntu', 'board')) {
    $keyPath = Join-Path $sshDirectory ('aura_5090_' + $role + '_ed25519')
    if (-not (Test-Path -LiteralPath $keyPath)) {
        $taskProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
        $taskProcessInfo.FileName = $keygen
        $taskProcessInfo.Arguments = '-q -t ed25519 -N "" -C "aura-5090-' + $role + '" -f "' + $keyPath + '"'
        $taskProcessInfo.UseShellExecute = $false
        $taskProcessInfo.CreateNoWindow = $true
        $taskProcessInfo.RedirectStandardOutput = $true
        $taskProcessInfo.RedirectStandardError = $true
        $taskProcess = New-Object System.Diagnostics.Process
        $taskProcess.StartInfo = $taskProcessInfo
        if (-not $taskProcess.Start()) { throw 'Could not start ssh-keygen.' }
        $taskProcess.WaitForExit()
        if ($taskProcess.ExitCode -ne 0) { throw 'ssh-keygen failed; existing key files were not overwritten.' }
        $taskProcess.Dispose()
    }
    $publicKey = $keyPath + '.pub'
    if (-not (Test-Path -LiteralPath $publicKey)) { throw 'Public key missing; do not overwrite the existing private key.' }
    Copy-Item -LiteralPath $publicKey -Destination (Join-Path $publicDirectory ($role + '.pub')) -Force
}
$utf8 = New-Object System.Text.UTF8Encoding($false)
$knownPath = Join-Path $sshDirectory 'aura_migration_known_hosts'
$knownLines = @()
if (Test-Path -LiteralPath $knownPath) { $knownLines += [IO.File]::ReadAllLines($knownPath) }
$knownLines += [IO.File]::ReadAllLines((Join-Path $migrationPackage 'codex/ssh/aura_migration_known_hosts'))
[IO.File]::WriteAllLines($knownPath, @($knownLines | Where-Object {$_} | Select-Object -Unique), $utf8)
$configPath = Join-Path $sshDirectory 'config'
$oldText = if (Test-Path -LiteralPath $configPath) {[IO.File]::ReadAllText($configPath)} else {''}
if ($oldText -match '(?m)^\s*Host\s+.*\baura-(ubuntu|kv260)\b') {
    $result.ssh_config_status = 'EXISTING_ALIAS_REQUIRES_REVIEW_NO_OVERWRITE'
} else {
    if (Test-Path -LiteralPath $configPath) {
        Copy-Item -LiteralPath $configPath -Destination ($configPath + '.before-aura-5090-' + (Get-Date -Format 'yyyyMMddHHmmss'))
    }
    $newBlock = [IO.File]::ReadAllText((Join-Path $migrationPackage 'codex/ssh/config.5090.template'))
    $newBlock = $newBlock.Replace('192.168.137.141', $UbuntuHost).Replace('192.168.50.2', $BoardHost)
    [IO.File]::WriteAllText($configPath, $oldText + "`r`n# BEGIN AURA 5090 MIGRATION`r`n" + $newBlock + "`r`n# END AURA 5090 MIGRATION`r`n", $utf8)
    $result.ssh_config_status = 'ALIASES_PREPARED_AUTHORIZATION_NOT_YET_TESTED'
}
$result.new_public_keys = $publicDirectory
$result.next_step = 'Authorize ubuntu.pub as ghmd on Ubuntu and board.pub as root on KV260 through their existing trusted console/session; then verify SSH host fingerprints and login.'
$result | ConvertTo-Json -Depth 6
