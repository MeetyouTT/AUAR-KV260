param(
    [ValidateSet('Check','Apply','Rollback')][string]$Action='Check',
    [string]$ExpectedSession
)
$ErrorActionPreference='Stop'
$name='AURA-5090-KV260-8797'
$support=Join-Path $PSScriptRoot 'parallel_lan'
$resultPath=Join-Path $support 'firewall_result.json'
$receiptPath=Join-Path $support 'firewall_creation_receipt.json'
. (Join-Path $support 'firewall_scope.ps1')

function Save-AuraFirewallJson([string]$Path,$Value) {
    $temporary=$Path+'.part-'+[guid]::NewGuid().ToString('N')
    try {
        [IO.File]::WriteAllText($temporary,($Value|ConvertTo-Json -Depth 16),[Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $temporary -Destination $Path -Force
        if($Path -eq $resultPath) {
            $history=Join-Path $support 'firewall_history'
            [IO.Directory]::CreateDirectory($history)|Out-Null
            $copy=Join-Path $history ([DateTime]::UtcNow.ToString('yyyyMMddTHHmmss')+'-'+[guid]::NewGuid().ToString('N')+'.json')
            Copy-Item -LiteralPath $Path -Destination $copy -ErrorAction Stop
        }
    } finally { if(Test-Path -LiteralPath $temporary){Remove-Item -LiteralPath $temporary} }
}

function Get-AuraOneActiveRule {
    $rules=@(Get-NetFirewallRule -PolicyStore ActiveStore -Name $name -ErrorAction SilentlyContinue)
    if($rules.Count -gt 1){throw 'Duplicate active rule names; no mutation applied'}
    if($rules.Count -eq 1){return $rules[0]}
    return $null
}

try {
    if($Action -ne 'Check') {
        $admin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        if(-not $admin){throw 'Windows administrator permission is required for Apply or Rollback'}
    }
    if($ExpectedSession -and $ExpectedSession -cnotmatch '^[0-9a-f]{32}$'){throw 'Explicit current session ID is invalid'}
    if($Action -eq 'Apply' -and -not $ExpectedSession){throw 'Apply requires the inspected current service session'}
    $adapter=Get-NetAdapter -InterfaceIndex 23 -ErrorAction Stop
    Assert-AuraDedicatedAdapterIdentity $adapter
    if($Action -ne 'Rollback') {
        if($adapter.Status -ne 'Up'){throw 'Dedicated physical Ethernet link is not up'}
        $address=@(Get-NetIPAddress -InterfaceIndex 23 -AddressFamily IPv4 -IPAddress '192.168.50.1' -ErrorAction Stop)
        if($address.Count -ne 1 -or $address[0].PrefixLength -ne 24 -or $address[0].AddressState -ne 'Preferred'){
            throw 'Dedicated host address is not ready'
        }
        $routes=@(Get-NetRoute -InterfaceIndex 23 -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue)
        if($routes.Count -ne 0){throw 'Dedicated adapter unexpectedly has a default route'}
    }
    $otherBefore=Get-AuraOtherFirewallFingerprint
    $guard=$null
    $guardAfter=$null
    if($Action -in @('Check','Apply')) {
        # The pinned Python guard has no alternate endpoint or bypass flag.
        # It requires complete local READY, accepted source hashes, live owner,
        # unique TTS, current health/listener, context 2048 and protected Ollama.
        $python='D:\AURARuntimes\voice-py310\Scripts\python.exe'
        $arguments=@('-B','-X','utf8',(Join-Path $support 'lan_control.py'),'firewall-guard')
        if($ExpectedSession){$arguments+=@('--expected-session',$ExpectedSession)}
        $guardText=(& $python @arguments | Out-String)
        if($LASTEXITCODE -ne 0){throw 'Complete local READY or fresh model owner/health guard failed'}
        $guard=$guardText|ConvertFrom-Json
        if($guard.status -ne 'FRESH_IDLE_MODEL_OWNER_CONFIRMED'){throw 'Unexpected guard result'}
        if($guard.adapter.alias -cne $adapter.Name){throw 'Dedicated adapter alias changed during validation'}
    }
    $existing=Get-AuraOneActiveRule
    if($Action -eq 'Rollback') {
        if(-not (Test-Path -LiteralPath $receiptPath)){throw 'No creation receipt; an existing rule cannot be adopted for removal'}
        $receipt=Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8|ConvertFrom-Json
        if($receipt.schema -ne 'aura-5090-firewall-creation-1' -or $receipt.created_by -ne 'configure_model_firewall.ps1 exact dedicated rule'){
            throw 'Invalid creation receipt; no rule removed'
        }
        if($existing) {
            $evidence=Get-AuraRuleEvidence $existing
            Assert-AuraExactFirewallScope $evidence $adapter.Name
            $fingerprint=Get-AuraSha256 ($evidence|ConvertTo-Json -Depth 8 -Compress)
            if($evidence.instance_id -cne $receipt.rule.instance_id -or $fingerprint -cne $receipt.rule_sha256){
                throw 'Rule identity or scope changed since creation; no removal applied'
            }
            $existing|Remove-NetFirewallRule -ErrorAction Stop
            if(Get-AuraOneActiveRule){throw 'Created rule removal is not confirmed'}
            $operation='REMOVED_EXACT_CREATED_RULE'
        } else { $operation='EXACT_CREATED_RULE_ALREADY_ABSENT' }
        $afterEvidence=$null
    } else {
        if($existing) {
            $evidence=Get-AuraRuleEvidence $existing
            Assert-AuraExactFirewallScope $evidence $adapter.Name
            $operation=if($Action -eq 'Check'){'CHECKED_EXACT_RULE'}else{'REUSED_EXACT_RULE'}
        } elseif($Action -eq 'Check') {
            throw 'Exact dedicated firewall rule is absent'
        } else {
            $persistent=@(Get-NetFirewallRule -PolicyStore PersistentStore -Name $name -ErrorAction SilentlyContinue)
            if($persistent.Count){throw 'Inactive persistent same-name rule exists; no overwrite applied'}
            $newParameters=@{
                PolicyStore='PersistentStore';Name=$name;DisplayName='AURA 5090 KV260 model inference'
                Direction='Inbound';Action='Allow';Enabled='True';Profile='Any';Protocol='TCP';LocalPort=8797
                LocalAddress='192.168.50.1';RemoteAddress='192.168.50.2';InterfaceAlias=$adapter.Name
                EdgeTraversalPolicy='Block';ErrorAction='Stop'
            }
            New-NetFirewallRule @newParameters | Out-Null
            $created=Get-AuraOneActiveRule
            if(-not $created){throw 'New rule is not present in ActiveStore'}
            $evidence=Get-AuraRuleEvidence $created
            Assert-AuraExactFirewallScope $evidence $adapter.Name
            if(Test-Path -LiteralPath $receiptPath) {
                $archive=Join-Path $support ('firewall_creation_receipt.before-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmss')+'-'+[guid]::NewGuid().ToString('N')+'.json')
                Copy-Item -LiteralPath $receiptPath -Destination $archive -ErrorAction Stop
            }
            $receipt=[ordered]@{schema='aura-5090-firewall-creation-1';created_by='configure_model_firewall.ps1 exact dedicated rule';utc=[DateTime]::UtcNow.ToString('o');service_session=$guard.session_id;rule=$evidence;rule_sha256=(Get-AuraSha256 ($evidence|ConvertTo-Json -Depth 8 -Compress));other_rules_before=$otherBefore}
            Save-AuraFirewallJson $receiptPath $receipt
            $operation='CREATED_EXACT_RULE'
        }
        $afterEvidence=Get-AuraRuleEvidence (Get-AuraOneActiveRule)
        Assert-AuraExactFirewallScope $afterEvidence $adapter.Name
        $guardAfterText=(& $python @arguments | Out-String)
        if($LASTEXITCODE -ne 0){throw 'Model owner or readiness changed during firewall verification'}
        $guardAfter=$guardAfterText|ConvertFrom-Json
        if($guardAfter.status -ne 'FRESH_IDLE_MODEL_OWNER_CONFIRMED' -or $guardAfter.session_id -cne $guard.session_id -or $guardAfter.configuration_sha256 -cne $guard.configuration_sha256 -or $guardAfter.adapter.alias -cne $adapter.Name){
            throw 'Current owner, configuration or physical interface changed during firewall verification'
        }
    }
    $otherAfter=Get-AuraOtherFirewallFingerprint
    if($otherAfter.sha256 -cne $otherBefore.sha256 -or $otherAfter.rule_count -ne $otherBefore.rule_count){
        throw 'Other firewall rules changed during this operation; inspect before continuing'
    }
    $result=[ordered]@{schema='aura-5090-firewall-result-1';status=$operation;requested_action=$Action;rule=$name;interface_index=23;interface_mac='C8-53-09-B0-89-DA';interface_guid='f14f89e5-18f4-483c-b22b-cd8010578636';interface_alias=$adapter.Name;scope=$afterEvidence;guard=$guard;guard_after=$guardAfter;other_rules_before=$otherBefore;other_rules_after=$otherAfter;other_rules_modified=$false;utc=[DateTime]::UtcNow.ToString('o')}
    Save-AuraFirewallJson $resultPath $result
    $result|ConvertTo-Json -Depth 16
} catch {
    $failure=[ordered]@{schema='aura-5090-firewall-result-1';status='FAILED';requested_action=$Action;error=$_.Exception.Message;utc=[DateTime]::UtcNow.ToString('o')}
    Save-AuraFirewallJson $resultPath $failure
    throw
}
