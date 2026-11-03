$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'firewall_scope.ps1')
$adapter=[pscustomobject]@{InterfaceIndex=23;InterfaceDescription='Intel(R) Ethernet Controller I226-V';MacAddress='C8-53-09-B0-89-DA';InterfaceGuid='f14f89e5-18f4-483c-b22b-cd8010578636';HardwareInterface=$true}
Assert-AuraDedicatedAdapterIdentity $adapter
foreach($key in @('InterfaceIndex','InterfaceDescription','MacAddress','InterfaceGuid','HardwareInterface')) {
    $changed=$adapter.PSObject.Copy()
    switch($key) {
        'InterfaceIndex' {$changed.$key=22}
        'InterfaceDescription' {$changed.$key='WAN Miniport (Network Monitor)'}
        'MacAddress' {$changed.$key='00-00-00-00-00-00'}
        'InterfaceGuid' {$changed.$key='00000000-0000-0000-0000-000000000000'}
        'HardwareInterface' {$changed.$key=$false}
    }
    $rejected=$false
    try { Assert-AuraDedicatedAdapterIdentity $changed } catch { $rejected=$true }
    if(-not $rejected){throw ('Changed physical adapter was accepted: '+$key)}
}
$good=[ordered]@{
    name='AURA-5090-KV260-8797';instance_id='isolated-test-rule';direction='Inbound';action='Allow'
    enabled='True';profile='Any';edge_traversal='Block';protocol='TCP';local_port=@('8797');remote_port=@('Any')
    local_address=@('192.168.50.1');remote_address=@('192.168.50.2');interface_alias=@('isolated-i226')
    program='Any';service='Any';policy_source_type='Local'
}
Assert-AuraExactFirewallScope $good 'isolated-i226'
$cases=@(
    @{key='direction';value='Outbound'},@{key='action';value='Block'},@{key='enabled';value='False'},
    @{key='local_port';value=@('8797','8792')},@{key='remote_port';value=@('5000')},
    @{key='local_address';value=@('Any')},@{key='remote_address';value=@('192.168.50.0/24')},
    @{key='interface_alias';value=@('Wi-Fi')},@{key='protocol';value='UDP'},
    @{key='profile';value='Public'},@{key='policy_source_type';value='GroupPolicy'},
    @{key='program';value='C:\unrelated.exe'},@{key='name';value='UnrelatedRule'}
)
foreach($case in $cases) {
    $changed=[ordered]@{}
    foreach($key in $good.Keys){$changed[$key]=$good[$key]}
    $changed[$case.key]=$case.value
    $rejected=$false
    try { Assert-AuraExactFirewallScope $changed 'isolated-i226' } catch { $rejected=$true }
    if(-not $rejected){throw ('Broadened or changed rule was accepted: '+$case.key)}
}
[ordered]@{status='PASS';accepted_exact_scopes=1;rejected_changed_scopes=$cases.Count;accepted_exact_adapter=1;rejected_changed_adapters=5;firewall_cmdlets_called=$false}|ConvertTo-Json
