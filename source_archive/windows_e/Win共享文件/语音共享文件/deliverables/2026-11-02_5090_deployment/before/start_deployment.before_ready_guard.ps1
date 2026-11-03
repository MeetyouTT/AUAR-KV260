param([ValidateSet('deploy','download','ollama')][string]$Role='deploy')
$ErrorActionPreference='Stop'
$deployRoot=$PSScriptRoot
$runnerPython='D:\AURARuntimes\download-py310\Scripts\python.exe'
$wrapper=Join-Path $deployRoot 'detached_worker.py'
$ownerName=switch($Role){'deploy'{'deployment_owner.json'}'download'{'download_owner.json'}'ollama'{'ollama_worker_owner.json'}}
$ownerPath=Join-Path $deployRoot $ownerName
if(Test-Path -LiteralPath $ownerPath){
    $previous=Get-Content -LiteralPath $ownerPath -Raw -Encoding UTF8|ConvertFrom-Json
    $current=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$previous.pid)
    if($current -and $current.CreationDate.ToUniversalTime().Ticks -eq ([DateTimeOffset]$previous.created_utc).UtcDateTime.Ticks -and $current.CommandLine -like ('*'+$wrapper+'*') -and $current.CommandLine -match ('\s'+[regex]::Escape($Role)+'(?:\s|$)')){
        [pscustomobject]@{status='ALREADY_RUNNING';role=$Role;pid=$previous.pid;state=(Join-Path $deployRoot 'STATUS.json')}|ConvertTo-Json
        return
    }
}
$commandLine='"'+$runnerPython+'" -I -B -X utf8 "'+$wrapper+'" '+$Role
$startup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$created=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$commandLine;CurrentDirectory=(Split-Path -Parent (Split-Path -Parent $deployRoot));ProcessStartupInformation=$startup}
if($created.ReturnValue -ne 0){throw ('Independent WMI worker creation failed: '+$created.ReturnValue)}
[pscustomobject]@{status='LAUNCHED';role=$Role;launcher_pid=[int]$created.ProcessId;creation='independent hidden WMI';owner_record=$ownerPath;state=(Join-Path $deployRoot 'STATUS.json')}|ConvertTo-Json
