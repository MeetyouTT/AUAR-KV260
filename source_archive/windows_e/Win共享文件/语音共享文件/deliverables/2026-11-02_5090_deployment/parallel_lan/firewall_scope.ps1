# Pure scope validation plus read-only evidence helpers. No rule is mutated here.
function Assert-AuraDedicatedAdapterIdentity($Adapter) {
    if($Adapter.InterfaceIndex -ne 23 -or
       $Adapter.InterfaceDescription -ne 'Intel(R) Ethernet Controller I226-V' -or
       ([string]$Adapter.MacAddress).ToUpperInvariant() -cne 'C8-53-09-B0-89-DA' -or
       ([guid]$Adapter.InterfaceGuid).ToString('D').ToLowerInvariant() -cne 'f14f89e5-18f4-483c-b22b-cd8010578636' -or
       -not $Adapter.HardwareInterface) {
        throw 'Dedicated physical Ethernet identity changed; no mutation applied'
    }
}

function Get-AuraSha256([string]$Value) {
    $algorithm=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($algorithm.ComputeHash([Text.Encoding]::UTF8.GetBytes($Value)))).Replace('-','').ToLowerInvariant() }
    finally { $algorithm.Dispose() }
}

function Assert-AuraExactFirewallScope($Evidence,[string]$Alias) {
    if ($null -eq $Evidence -or
        $Evidence.name -cne 'AURA-5090-KV260-8797' -or
        $Evidence.direction -ne 'Inbound' -or $Evidence.action -ne 'Allow' -or
        $Evidence.enabled -ne 'True' -or $Evidence.profile -ne 'Any' -or
        $Evidence.edge_traversal -ne 'Block' -or $Evidence.protocol -notin @('TCP','6') -or
        @($Evidence.local_port).Count -ne 1 -or $Evidence.local_port[0] -ne '8797' -or
        @($Evidence.remote_port).Count -ne 1 -or $Evidence.remote_port[0] -ne 'Any' -or
        @($Evidence.local_address).Count -ne 1 -or $Evidence.local_address[0] -ne '192.168.50.1' -or
        @($Evidence.remote_address).Count -ne 1 -or $Evidence.remote_address[0] -ne '192.168.50.2' -or
        @($Evidence.interface_alias).Count -ne 1 -or $Evidence.interface_alias[0] -cne $Alias -or
        $Evidence.program -ne 'Any' -or $Evidence.service -ne 'Any' -or
        $Evidence.policy_source_type -ne 'Local') {
        throw 'Existing rule differs from the exact dedicated-board scope; no overwrite or removal applied'
    }
}

function Get-AuraRuleEvidence($Rule) {
    if (@($Rule).Count -ne 1) { throw 'Exactly one rule is required' }
    $ports=@($Rule|Get-NetFirewallPortFilter -ErrorAction Stop)
    $addresses=@($Rule|Get-NetFirewallAddressFilter -ErrorAction Stop)
    $interfaces=@($Rule|Get-NetFirewallInterfaceFilter -ErrorAction Stop)
    $applications=@($Rule|Get-NetFirewallApplicationFilter -ErrorAction Stop)
    $services=@($Rule|Get-NetFirewallServiceFilter -ErrorAction Stop)
    if ($ports.Count -ne 1 -or $addresses.Count -ne 1 -or $interfaces.Count -ne 1 -or $applications.Count -ne 1 -or $services.Count -ne 1) {
        throw 'Unexpected rule filter multiplicity'
    }
    return [ordered]@{
        name=[string]$Rule.Name; instance_id=[string]$Rule.InstanceID
        direction=[string]$Rule.Direction; action=[string]$Rule.Action; enabled=[string]$Rule.Enabled
        profile=[string]$Rule.Profile; edge_traversal=[string]$Rule.EdgeTraversalPolicy
        policy_source_type=[string]$Rule.PolicyStoreSourceType; protocol=[string]$ports[0].Protocol
        local_port=@($ports[0].LocalPort|ForEach-Object{[string]$_}|Sort-Object)
        remote_port=@($ports[0].RemotePort|ForEach-Object{[string]$_}|Sort-Object)
        local_address=@($addresses[0].LocalAddress|ForEach-Object{[string]$_}|Sort-Object)
        remote_address=@($addresses[0].RemoteAddress|ForEach-Object{[string]$_}|Sort-Object)
        interface_alias=@($interfaces[0].InterfaceAlias|ForEach-Object{[string]$_}|Sort-Object)
        program=[string]$applications[0].Program; service=[string]$services[0].Service
    }
}

function Get-AuraOtherFirewallFingerprint {
    $rules=@(Get-NetFirewallRule -PolicyStore PersistentStore -ErrorAction Stop | Where-Object { $_.Name -ne 'AURA-5090-KV260-8797' })
    $value=[ordered]@{
        rules=@($rules|Sort-Object Name,InstanceID|Select-Object Name,InstanceID,Enabled,Direction,Action,Profile,EdgeTraversalPolicy)
        ports=@($rules|Get-NetFirewallPortFilter|Sort-Object InstanceID|Select-Object InstanceID,Protocol,LocalPort,RemotePort,DynamicTarget)
        addresses=@($rules|Get-NetFirewallAddressFilter|Sort-Object InstanceID|Select-Object InstanceID,LocalAddress,RemoteAddress)
        interfaces=@($rules|Get-NetFirewallInterfaceFilter|Sort-Object InstanceID|Select-Object InstanceID,InterfaceAlias)
        applications=@($rules|Get-NetFirewallApplicationFilter|Sort-Object InstanceID|Select-Object InstanceID,Program,Package)
        services=@($rules|Get-NetFirewallServiceFilter|Sort-Object InstanceID|Select-Object InstanceID,Service)
    }
    return [ordered]@{rule_count=$rules.Count; sha256=(Get-AuraSha256 ($value|ConvertTo-Json -Depth 8 -Compress)); scope='Other PersistentStore rule properties and port/address/interface/application/service filters'}
}
