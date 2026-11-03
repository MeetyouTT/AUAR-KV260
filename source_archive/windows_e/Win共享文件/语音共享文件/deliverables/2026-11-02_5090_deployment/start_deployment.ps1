param([ValidateSet('deploy','download','ollama')][string]$Role='deploy')
$ErrorActionPreference='Stop'
$deployRoot=$PSScriptRoot
$runnerPython='D:\AURARuntimes\download-py310\Scripts\python.exe'
$wrapper=Join-Path $deployRoot 'detached_worker.py'
$ownerName=switch($Role){'deploy'{'deployment_owner.json'}'download'{'download_owner.json'}'ollama'{'ollama_worker_owner.json'}}
$ownerPath=Join-Path $deployRoot $ownerName
if($Role -eq 'deploy' -and (Test-Path -LiteralPath (Join-Path $deployRoot 'STATUS.json'))){
    $saved=Get-Content -LiteralPath (Join-Path $deployRoot 'STATUS.json') -Raw -Encoding UTF8|ConvertFrom-Json
    if($saved.complete -eq $true){
        $ready=Get-Content -LiteralPath (Join-Path $deployRoot 'READY_LOCAL.json') -Raw -Encoding UTF8|ConvertFrom-Json
        if($ready.status -ne 'READY_LOCAL_ONLY_BOARD_INTEGRATION_PENDING' -or $ready.endpoint -ne 'http://127.0.0.1:8797'){
            throw 'Completed deployment receipt needs review; no duplicate worker was launched'
        }
        $health=Invoke-RestMethod -Uri ($ready.endpoint+'/health') -TimeoutSec 3
        if($health.protocol_version -ne 1 -or $health.role -ne 'model_inference_only' -or $health.backend.tts_ready -ne $true){
            throw 'Completed deployment is not currently healthy; inspect the service owner before restarting'
        }
        [pscustomobject]@{status='ALREADY_COMPLETE';role=$Role;endpoint=$ready.endpoint;state=(Join-Path $deployRoot 'STATUS.json')}|ConvertTo-Json
        return
    }
}
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
