$ErrorActionPreference='Stop'
$asrResult=[ordered]@{status='STARTING';local_address='192.168.50.1';remote_address='192.168.50.2';port=8791}
try {
    $asrName='AURA-KV260-ASR-20261018'
    $asrAdapter=@(Get-NetAdapter | Where-Object {$_.MacAddress -eq '30-56-0F-D8-4E-0A'})
    if ($asrAdapter.Count -ne 1) {throw 'Verified wired adapter not found'}
    $asrRule=Get-NetFirewallRule -Name $asrName -ErrorAction SilentlyContinue
    if ($asrRule) {
        $asrAddress=$asrRule | Get-NetFirewallAddressFilter
        $asrPorts=$asrRule | Get-NetFirewallPortFilter
        if ($asrAddress.LocalAddress -ne '192.168.50.1' -or $asrAddress.RemoteAddress -ne '192.168.50.2' -or $asrPorts.LocalPort -ne 8791) {
            throw 'Existing named firewall rule differs; not modifying it'
        }
    } else {
        New-NetFirewallRule -Name $asrName -DisplayName 'AURA KV260 wired ASR only' -Direction Inbound -Action Allow -Enabled True -Profile Any -Protocol TCP -LocalPort 8791 -LocalAddress '192.168.50.1' -RemoteAddress '192.168.50.2' -InterfaceAlias $asrAdapter[0].Name | Out-Null
    }
    $asrResult.status='READY'
    $asrResult.rule_name=$asrName
} catch {$asrResult.status='FAILED';$asrResult.error=$_.Exception.Message}
$asrResult | ConvertTo-Json | Out-File -LiteralPath (Join-Path $PSScriptRoot 'asr_firewall_result.json') -Encoding utf8
