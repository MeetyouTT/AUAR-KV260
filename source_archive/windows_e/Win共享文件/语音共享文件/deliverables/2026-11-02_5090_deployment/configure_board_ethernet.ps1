param([int]$InterfaceIndex=22)
$ErrorActionPreference='Stop'
$recordPath=Join-Path $PSScriptRoot 'network_setup_result.json'
try{
    $admin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if(-not $admin){throw 'Windows administrator permission is required for the dedicated Ethernet address'}
    $adapter=Get-NetAdapter -InterfaceIndex $InterfaceIndex
    if($adapter.InterfaceDescription -ne 'Intel(R) Ethernet Controller I226-V' -or -not $adapter.HardwareInterface){throw 'Dedicated physical adapter identity changed'}
    $addresses=@(Get-NetIPAddress -InterfaceIndex $InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue)
    $before=[ordered]@{adapter=($adapter|Select-Object Name,InterfaceIndex,InterfaceDescription,Status,MacAddress);ipv4=@($addresses|Select-Object IPAddress,PrefixLength,PrefixOrigin);interface=(Get-NetIPInterface -InterfaceIndex $InterfaceIndex -AddressFamily IPv4|Select-Object Dhcp,InterfaceMetric);default_routes=@(Get-NetRoute -InterfaceIndex $InterfaceIndex -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue|Select-Object DestinationPrefix,NextHop)}
    $backup=Join-Path $PSScriptRoot 'network_before.json'
    if(-not(Test-Path -LiteralPath $backup)){[IO.File]::WriteAllText($backup,($before|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))}
    $foreign=@($addresses|Where-Object {$_.IPAddress -notlike '169.254.*' -and $_.IPAddress -ne '192.168.50.1'})
    if($foreign.Count){throw 'Unexpected existing IPv4 on the dedicated adapter; no changes applied'}
    if(-not @($addresses|Where-Object {$_.IPAddress -eq '192.168.50.1' -and $_.PrefixLength -eq 24}).Count){
        New-NetIPAddress -InterfaceIndex $InterfaceIndex -IPAddress '192.168.50.1' -PrefixLength 24 -AddressFamily IPv4|Out-Null
    }
    $after=Get-NetIPAddress -InterfaceIndex $InterfaceIndex -AddressFamily IPv4 -IPAddress '192.168.50.1'
    $result=[ordered]@{status='ETHERNET_ADDRESS_CONFIGURED';interface_index=$InterfaceIndex;address=$after.IPAddress;prefix_length=$after.PrefixLength;address_state=[string]$after.AddressState;default_gateway_added=$false;dns_modified=$false;wifi_modified=$false;board_commands_sent=$false;utc=[DateTime]::UtcNow.ToString('o')}
    [IO.File]::WriteAllText($recordPath,($result|ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
}catch{
    $result=[ordered]@{status='FAILED';error=$_.Exception.Message;board_commands_sent=$false;utc=[DateTime]::UtcNow.ToString('o')}
    [IO.File]::WriteAllText($recordPath,($result|ConvertTo-Json),[Text.UTF8Encoding]::new($false));throw
}