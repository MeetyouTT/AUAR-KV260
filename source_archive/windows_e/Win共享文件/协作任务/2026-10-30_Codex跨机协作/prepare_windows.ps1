# Run in PowerShell 7. Creates a dedicated key without changing existing SSH access.
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$sshRoot = Join-Path $env:USERPROFILE '.ssh'
$keyPath = Join-Path $sshRoot 'aura_codex_ubuntu_ed25519'
$publicKeyPath = "$keyPath.pub"
$sharedPublicKeyPath = Join-Path $taskRoot 'windows-codex.pub'

if (-not (Test-Path -LiteralPath $sshRoot)) {
    New-Item -ItemType Directory -Path $sshRoot | Out-Null
}
if ((Test-Path -LiteralPath $keyPath) -xor (Test-Path -LiteralPath $publicKeyPath)) {
    throw 'Incomplete dedicated key pair exists. Inspect it instead of overwriting it.'
}
$created = $false
if (-not (Test-Path -LiteralPath $keyPath)) {
    $keygen = (Get-Command ssh-keygen.exe -ErrorAction Stop).Source
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $keygen
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    foreach ($argument in @('-t', 'ed25519', '-f', $keyPath, '-N', '', '-C', 'aura-codex-windows-to-ubuntu')) {
        $startInfo.ArgumentList.Add($argument)
    }
    $taskProcess = [System.Diagnostics.Process]::new()
    $taskProcess.StartInfo = $startInfo
    if (-not $taskProcess.Start()) { throw 'Could not start ssh-keygen.' }
    $keygenOutput = $taskProcess.StandardOutput.ReadToEnd()
    $keygenError = $taskProcess.StandardError.ReadToEnd()
    $taskProcess.WaitForExit()
    if ($taskProcess.ExitCode -ne 0) { throw "ssh-keygen failed: $keygenError" }
    $created = $true
}

# Keep only the current account and Windows system/administrator access.
# icacls updates the existing DACL without requesting SACL/owner privileges.
# Never copy the private key to the share.
$taskIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$taskGrant = '*' + $taskIdentity.User.Value + ':(F)'
& icacls.exe $keyPath /inheritance:r /grant:r $taskGrant | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not restrict the private key ACL.' }
$taskAcl = Get-Acl -LiteralPath $keyPath
$taskAllowedSids = @($taskIdentity.User.Value, 'S-1-5-18', 'S-1-5-32-544')
foreach ($taskAccessRule in $taskAcl.Access) {
    if ($taskAccessRule.AccessControlType -eq [System.Security.AccessControl.AccessControlType]::Allow) {
        $taskAccessSid = $taskAccessRule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
        if ($taskAccessSid -notin $taskAllowedSids) { throw 'Unexpected private-key access remains; inspect the ACL.' }
    }
}

$publicKey = (Get-Content -LiteralPath $publicKeyPath -Raw).Trim()
if ($publicKey -notmatch '^ssh-ed25519 [A-Za-z0-9+/]+={0,2}(?: .*)?$') {
    throw 'Unexpected public key format.'
}
[System.IO.File]::WriteAllText($sharedPublicKeyPath, "$publicKey`n", [System.Text.UTF8Encoding]::new($false))
$fingerprint = (& ssh-keygen.exe -lf $publicKeyPath | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not fingerprint the public key.' }
$configPath = Join-Path $sshRoot 'config'
$registrationPath = Join-Path $taskRoot 'ubuntu-registration.json'
$result = [ordered]@{
    schema_version = 1
    updated_at = [DateTimeOffset]::UtcNow.ToString('o')
    status = 'WAITING_FOR_UBUNTU_REGISTRATION'
    dedicated_key_created_this_run = $created
    private_key_path = $keyPath
    private_key_shared = $false
    public_key_path = $sharedPublicKeyPath
    public_key_fingerprint = $fingerprint
    ssh_config_exists = (Test-Path -LiteralPath $configPath)
    ssh_config_modified = $false
    registration_present = (Test-Path -LiteralPath $registrationPath)
    remote_ssh_verified = $false
    app_remote_project_verified = $false
}
$resultJson = $result | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText((Join-Path $taskRoot 'windows-preparation.json'), "$resultJson`n", [System.Text.UTF8Encoding]::new($false))
$resultJson
