param([switch]$RestoreDhcp, [ValidateSet('192.168.50.1','192.168.50.3')][string]$HostAddress='192.168.50.1')
$ErrorActionPreference = 'Stop'
$netOutput = $PSScriptRoot
$netResult = [ordered]@{ status='STARTING'; adapter_mac='30-56-0F-D8-4E-0A'; host_ip=$HostAddress; prefix=24; board_ip='192.168.50.2'; wifi_modified=$false }
$netChanged = $false
try {
    $netAdmin = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $netAdmin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Administrator token required' }
    $netAdapters = @(Get-NetAdapter | Where-Object { $_.MacAddress -eq $netResult.adapter_mac })
    if ($netAdapters.Count -ne 1) { throw 'Expected exactly one verified Realtek wired adapter' }
    $netAdapter = $netAdapters[0]
    if ($netAdapter.Status -ne 'Up') { throw 'Wired adapter link is not up' }
    $netIndex = $netAdapter.ifIndex
    $netResult.interface_index = $netIndex
    $netResult.interface_name = $netAdapter.Name
    if ($RestoreDhcp) {
        Get-NetIPAddress -InterfaceIndex $netIndex -AddressFamily IPv4 | Where-Object { $_.IPAddress -in @('192.168.50.1','192.168.50.3') } | Remove-NetIPAddress -Confirm:$false
        Set-NetIPInterface -InterfaceIndex $netIndex -AddressFamily IPv4 -Dhcp Enabled
        $netResult.status = 'RESTORED_DHCP'
    } else {
        $netOriginal = @(Get-NetIPAddress -InterfaceIndex $netIndex -AddressFamily IPv4)
        $netWasDhcp = (Get-NetIPInterface -InterfaceIndex $netIndex -AddressFamily IPv4).Dhcp
        $netExistingManual = @($netOriginal | Where-Object { $_.IPAddress -notlike '169.254.*' -and $_.IPAddress -notin @('192.168.50.1','192.168.50.3') })
        if ($netExistingManual.Count -gt 0) { throw 'Wired interface gained another IPv4 configuration; stopped before changes' }
        if (Test-Path -LiteralPath (Join-Path $netOutput 'wired_before.clixml')) {
            if (-not ($netOriginal | Where-Object { $_.IPAddress -in @('192.168.50.1','192.168.50.3') })) { throw 'Backup exists but wired address differs; inspect before reconfiguration' }
        } else {
            [pscustomobject]@{
                adapter=$netAdapter; addresses=$netOriginal
                ip_interface=(Get-NetIPInterface -InterfaceIndex $netIndex -AddressFamily IPv4)
                dns=(Get-DnsClientServerAddress -InterfaceIndex $netIndex -AddressFamily IPv4)
                routes=@(Get-NetRoute -InterfaceIndex $netIndex -AddressFamily IPv4)
            } | Export-Clixml -LiteralPath (Join-Path $netOutput 'wired_before.clixml')
        }
        if (-not ($netOriginal | Where-Object { $_.IPAddress -eq $HostAddress })) {
            $netChanged = $true
            Set-NetIPInterface -InterfaceIndex $netIndex -AddressFamily IPv4 -Dhcp Disabled
            New-NetIPAddress -InterfaceIndex $netIndex -AddressFamily IPv4 -IPAddress $HostAddress -PrefixLength 24 | Out-Null
        }
        for ($netTry=0; $netTry -lt 12; $netTry++) {
            $netAddress = Get-NetIPAddress -InterfaceIndex $netIndex -IPAddress $HostAddress -AddressFamily IPv4
            if ($netAddress.AddressState -eq 'Preferred') { break }
            if ($netAddress.AddressState -eq 'Duplicate') { throw 'Address conflict detected; restoring DHCP' }
            Start-Sleep -Seconds 1
        }
        if ($netAddress.AddressState -ne 'Preferred') { throw 'Wired address did not become Preferred' }
        Get-NetIPAddress -InterfaceIndex $netIndex -AddressFamily IPv4 | Where-Object { $_.IPAddress -in @('192.168.50.1','192.168.50.3') -and $_.IPAddress -ne $HostAddress } | Remove-NetIPAddress -Confirm:$false
        $netResult.status = 'CONFIGURED'
        $netResult.address_state = [string]$netAddress.AddressState
        $netResult.routes = @(Get-NetRoute -InterfaceIndex $netIndex -AddressFamily IPv4 | Select-Object DestinationPrefix,NextHop,RouteMetric)
        $netResult.persistent_addresses = @(Get-NetIPAddress -InterfaceIndex $netIndex -AddressFamily IPv4 -PolicyStore PersistentStore | Select-Object IPAddress,PrefixLength)
        $netResult.board_ping = [bool](Test-Connection -ComputerName '192.168.50.2' -Count 2 -Quiet -ErrorAction SilentlyContinue)
        $netResult.board_neighbor = @(Get-NetNeighbor -InterfaceIndex $netIndex -AddressFamily IPv4 | Where-Object { $_.IPAddress -eq '192.168.50.2' } | Select-Object IPAddress,LinkLayerAddress,State)
    }
} catch {
    $netResult.status = 'FAILED'
    $netResult.error = $_.Exception.Message
    if ($netChanged) {
        try {
            Get-NetIPAddress -InterfaceIndex $netIndex -AddressFamily IPv4 | Where-Object { $_.IPAddress -eq $HostAddress } | Remove-NetIPAddress -Confirm:$false
            if ($netWasDhcp -eq 'Enabled') {
                Set-NetIPInterface -InterfaceIndex $netIndex -AddressFamily IPv4 -Dhcp Enabled
                $netResult.rollback = 'DHCP_RESTORED'
            } else { $netResult.rollback = 'PREVIOUS_STATIC_ADDRESS_RETAINED' }
        } catch { $netResult.rollback_error = $_.Exception.Message }
    }
} finally {
    $netResult | ConvertTo-Json -Depth 7 | Out-File -LiteralPath (Join-Path $netOutput 'wired_setup_result.json') -Encoding utf8
}
