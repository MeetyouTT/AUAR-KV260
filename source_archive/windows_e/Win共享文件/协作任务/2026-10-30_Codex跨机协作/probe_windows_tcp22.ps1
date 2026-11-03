# Read-only Windows probe. No route, VPN, firewall, SSH config or model changes.
param([string]$UbuntuHost = '')
$ErrorActionPreference='Stop'
$hostSource='argument'
if ([string]::IsNullOrWhiteSpace($UbuntuHost)) {
    $registration=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'ubuntu-registration.json') -Raw | ConvertFrom-Json
    $UbuntuHost=[string]$registration.host
    $hostSource='ubuntu-registration.json'
}
$parsedUbuntuAddress=$null
if (-not [Net.IPAddress]::TryParse($UbuntuHost,[ref]$parsedUbuntuAddress) -or
    $parsedUbuntuAddress.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or
    [Net.IPAddress]::IsLoopback($parsedUbuntuAddress)) {
    throw 'Provide the current Ubuntu IPv4 address or update ubuntu-registration.json first.'
}
$sshPort=22
$report=[ordered]@{
    schema_version=1
    status='CHECKING'
    started_utc=[DateTime]::UtcNow.ToString('o')
    ubuntu_host=$ubuntuHost
    host_source=$hostSource
    port=$sshPort
    routes_modified=$false
    vpn_modified=$false
    ssh_config_modified=$false
    authentication_attempted=$false
}
try {
    $report.route=@(Find-NetRoute -RemoteIPAddress $ubuntuHost | Select-Object IPAddress,InterfaceAlias,InterfaceIndex,DestinationPrefix,NextHop,RouteMetric)
    $report.route_query_method='Find-NetRoute'
} catch {
    $report.route_query_error=$_.Exception.Message
    $report.route_query_method='route.exe -4 PRINT'
    $report.route_table_text=(& route.exe -4 PRINT | Out-String).Trim()
}
$attempts=@()
for($index=0;$index -lt 3;$index++) {
    $client=[Net.Sockets.TcpClient]::new()
    $attempt=[ordered]@{index=$index;started_utc=[DateTime]::UtcNow.ToString('o');connected=$false;banner=$null}
    try {
        $task=$client.ConnectAsync($ubuntuHost,$sshPort)
        if (-not $task.Wait(5000)) {throw 'TCP connect timed out after 5000 ms'}
        $null=$task.GetAwaiter().GetResult()
        $attempt.connected=$client.Connected
        $attempt.local_endpoint=$client.Client.LocalEndPoint.ToString()
        $stream=$client.GetStream()
        $stream.ReadTimeout=5000
        $buffer=New-Object byte[] 256
        $count=$stream.Read($buffer,0,$buffer.Length)
        $attempt.banner=[Text.Encoding]::ASCII.GetString($buffer,0,$count).Trim()
    } catch {
        $attempt.error=$_.Exception.Message
        if ($client.Client.LocalEndPoint) {$attempt.local_endpoint=$client.Client.LocalEndPoint.ToString()}
    } finally {
        $client.Dispose()
        $attempt.finished_utc=[DateTime]::UtcNow.ToString('o')
        $attempts+=[pscustomobject]$attempt
    }
    if ($index -lt 2) {Start-Sleep -Seconds 2}
}
$report.attempts=$attempts
$report.finished_utc=[DateTime]::UtcNow.ToString('o')
$report.status=if (@($attempts | Where-Object {$_.banner -like 'SSH-*'}).Count -gt 0) {'SSH_BANNER_RECEIVED'} else {'SSH_BANNER_NOT_RECEIVED'}
$target=Join-Path $PSScriptRoot 'windows-tcp22-probe.json'
$temporary=$target+'.tmp'
$report | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $temporary -Encoding utf8
Move-Item -LiteralPath $temporary -Destination $target -Force
$report | ConvertTo-Json -Depth 7
