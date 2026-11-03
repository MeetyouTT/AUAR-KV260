$ErrorActionPreference = 'Stop'
$downloadRoot = Join-Path $env:USERPROFILE 'Downloads'

if (-not (Test-Path -LiteralPath $downloadRoot -PathType Container)) {
    throw "找不到下载文件夹：$downloadRoot"
}

$allFiles = @(Get-ChildItem -LiteralPath $downloadRoot -File -Recurse -ErrorAction SilentlyContinue)
$tarCommand = Get-Command tar.exe -ErrorAction SilentlyContinue
$checks = @(
    @{ Label = 'Vivado/Vitis 2022.2 Linux 安装器'; Pattern = '^Xilinx_Unified_2022\.2_1014_8888_Lin64\.bin$'; Kind = 'Xilinx' },
    @{ Label = 'PetaLinux 2022.2 安装器'; Pattern = '^petalinux-v2022\.2-10141622-installer\.run$'; Kind = 'PetaLinux' },
    @{ Label = 'KV260 2022.2 BSP'; Pattern = '^xilinx-kv260-starterkit-v2022\.2-10141622\.bsp$'; Kind = 'Archive' },
    @{ Label = 'Vitis AI 3.0 源码 ZIP'; Pattern = '^(Vitis-AI.*3[._-]?0|v3[._-]?0).*\.zip$'; Kind = 'Archive' }
)

$results = foreach ($check in $checks) {
    $found = @($allFiles | Where-Object { $_.Name -match $check.Pattern })

    if ($found.Count -eq 0) {
        [pscustomobject]@{
            项目 = $check.Label
            状态 = '未找到'
            大小 = ''
            检查结果 = '未在 Windows“下载”文件夹中找到'
            路径 = ''
        }
        continue
    }

    if ($found.Count -gt 1) {
        [pscustomobject]@{
            项目 = $check.Label
            状态 = '找到多个'
            大小 = ''
            检查结果 = '请人工确认哪一份是要使用的文件'
            路径 = ($found.FullName -join ' | ')
        }
        continue
    }

    $file = $found[0]
    $status = '需核对'
    $detail = ''

    try {
        switch ($check.Kind) {
            'Xilinx' {
                $expectedBytes = 284181282
                $expectedSha256 = '5C1E4768DE41F9A01480A7305D0A8C2E9DA0EF091BFEE0487F6F8160511083B7'
                $sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
                $sizeOK = ($file.Length -eq $expectedBytes)
                $hashOK = ($sha256 -ieq $expectedSha256)
                $status = if ($sizeOK -and $hashOK) { '通过' } else { '需核对' }
                $detail = "大小匹配=$sizeOK；SHA256与此前检查文件匹配=$hashOK；SHA256=$sha256"
            }
            'PetaLinux' {
                $expectedBytes = 2774984002
                $expectedMd5 = '8ee3e168ed891b467d248789cea8e484'
                $expectedSha256 = '4B8FF9128C991C757C55266B09EB2E83D2E420C2830159C6A081806DCA3A3197'
                $md5 = (Get-FileHash -LiteralPath $file.FullName -Algorithm MD5).Hash
                $sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
                $sizeOK = ($file.Length -eq $expectedBytes)
                $md5OK = ($md5 -ieq $expectedMd5)
                $shaOK = ($sha256 -ieq $expectedSha256)
                $status = if ($sizeOK -and $md5OK -and $shaOK) { '通过' } else { '需核对' }
                $detail = "大小匹配=$sizeOK；AMD页面MD5匹配=$md5OK；SHA256与此前检查文件匹配=$shaOK；SHA256=$sha256"
            }
            'Archive' {
                if (-not $tarCommand) {
                    $status = '未完成'
                    $detail = 'Windows找不到 tar.exe，无法检查压缩包'
                }
                else {
                    $entries = @(& $tarCommand.Source -tf $file.FullName 2>$null)
                    $tarExit = $LASTEXITCODE
                    $sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
                    $status = if ($tarExit -eq 0 -and $entries.Count -gt 0) { '可读取' } else { '压缩包检查失败' }
                    $detail = "tar退出码=$tarExit；目录项数=$($entries.Count)；SHA256=$sha256"
                }
            }
        }
    }
    catch {
        $status = '检查出错'
        $detail = $_.Exception.Message
    }

    [pscustomobject]@{
        项目 = $check.Label
        状态 = $status
        大小 = '{0:N0} bytes ({1:N2} GB)' -f $file.Length, ($file.Length / 1GB)
        检查结果 = $detail
        路径 = $file.FullName
    }
}

Write-Host "下载目录：$downloadRoot`n" -ForegroundColor Cyan
$results | Format-List

$partialFiles = @($allFiles | Where-Object { $_.Name -match '(?i)(\.crdownload|\.part|\.partial|\.download)$' })
if ($partialFiles.Count -gt 0) {
    Write-Host '发现可能未下载完成的临时文件：' -ForegroundColor Yellow
    $partialFiles | Select-Object FullName, Length | Format-Table -AutoSize
}
else {
    Write-Host '未发现常见的未完成下载临时文件。' -ForegroundColor Green
}

Write-Host '说明：BSP/源码 ZIP 显示“可读取”表示压缩包目录可打开；没有官方校验值时，这不能证明文件与发布服务器逐字节相同。'
