$ErrorActionPreference='Stop'
$name='AURA-5090-KV260-8797'
$resultPath=Join-Path $PSScriptRoot 'model_firewall_result.json'
try{
    $admin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if(-not $admin){throw 'Windows administrator permission is required'}
    $ready=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'READY_LOCAL.json') -Raw -Encoding UTF8|ConvertFrom-Json
    $status=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'STATUS.json') -Raw -Encoding UTF8|ConvertFrom-Json
    if($status.complete -ne $true -or $ready.status -ne 'READY_LOCAL_ONLY_BOARD_INTEGRATION_PENDING' -or $ready.weights_sha256 -ne 'd83adbbbaace8acdfcfe28004f779326176b9df00b4ec99dc6c24d749723d3b9'){
        throw 'Original local model verification must complete before adding board access'
    }
    $health=Invoke-RestMethod -Uri 'http://127.0.0.1:8797/health' -TimeoutSec 3
    if($health.protocol_version -ne 1 -or $health.role -ne 'model_inference_only' -or $health.backend.tts_ready -ne $true){throw 'Local model service is not currently ready'}
    $adapter=Get-NetAdapter -InterfaceIndex 22
    if($adapter.InterfaceDescription -ne 'Intel(R) Ethernet Controller I226-V' -or -not $adapter.HardwareInterface -or $adapter.Status -ne 'Up'){
        throw 'Dedicated physical Ethernet adapter identity or link changed'
    }
    $address=Get-NetIPAddress -InterfaceIndex 22 -AddressFamily IPv4 -IPAddress '192.168.50.1'
    if($address.PrefixLength -ne 24 -or $address.AddressState -ne 'Preferred'){throw 'Dedicated host address is not ready'}
    $existing=Get-NetFirewallRule -Name $name -ErrorAction SilentlyContinue
    if($existing){
        $ports=$existing|Get-NetFirewallPortFilter
        $addresses=$existing|Get-NetFirewallAddressFilter
        $interfaces=$existing|Get-NetFirewallInterfaceFilter
        if($existing.Direction -ne 'Inbound' -or $existing.Action -ne 'Allow' -or $existing.Enabled -ne 'True' -or $ports.Protocol -notin @('TCP','6') -or $ports.LocalPort -ne '8797' -or @($addresses.LocalAddress).Count -ne 1 -or $addresses.LocalAddress[0] -ne '192.168.50.1' -or @($addresses.RemoteAddress).Count -ne 1 -or $addresses.RemoteAddress[0] -ne '192.168.50.2' -or @($interfaces.InterfaceAlias).Count -ne 1 -or $interfaces.InterfaceAlias[0] -ne $adapter.Name){
            throw 'Existing rule differs from the exact dedicated-board scope; no overwrite applied'
        }
        $action='REUSED_EXACT_RULE'
    }else{
        New-NetFirewallRule -Name $name -DisplayName 'AURA 5090 KV260 model inference' -Direction Inbound -Action Allow -Enabled True -Profile Any -Protocol TCP -LocalPort 8797 -LocalAddress '192.168.50.1' -RemoteAddress '192.168.50.2' -InterfaceAlias $adapter.Name -EdgeTraversalPolicy Block|Out-Null
        $action='CREATED_EXACT_RULE'
    }
    $result=[ordered]@{status=$action;rule=$name;local_address='192.168.50.1';remote_address='192.168.50.2';tcp_port=8797;interface_index=22;other_rules_modified=$false;utc=[DateTime]::UtcNow.ToString('o')}
    $result|ConvertTo-Json|Set-Content -LiteralPath $resultPath -Encoding utf8
}catch{
    [ordered]@{status='FAILED';error=$_.Exception.Message;utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath $resultPath -Encoding utf8
    throw
}
