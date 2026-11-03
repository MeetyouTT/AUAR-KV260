$ErrorActionPreference='Stop'
$lan='E:\Win共享文件\语音共享文件\deliverables\2026-11-02_5090_deployment\parallel_lan'
. (Join-Path $lan 'firewall_scope.ps1')
$timer=[Diagnostics.Stopwatch]::StartNew()
$fingerprint=Get-AuraOtherFirewallFingerprint
$timer.Stop()
$active=@(Get-NetFirewallRule -PolicyStore ActiveStore -Name 'AURA-5090-KV260-8797' -ErrorAction SilentlyContinue)
$persistent=@(Get-NetFirewallRule -PolicyStore PersistentStore -Name 'AURA-5090-KV260-8797' -ErrorAction SilentlyContinue)
$result=[ordered]@{schema='aura-firewall-readonly-fingerprint-timing-1';utc=[DateTime]::UtcNow.ToString('o');powershell_version=$PSVersionTable.PSVersion.ToString();elapsed_ms=$timer.Elapsed.TotalMilliseconds;fingerprint=$fingerprint;dedicated_rule_active_count=$active.Count;dedicated_rule_persistent_count=$persistent.Count;firewall_modified=$false;model_control_performed=$false;inference_sent=$false;board_contacted=$false}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'fingerprint_timing.json'),($result|ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
$result|ConvertTo-Json -Depth 5
