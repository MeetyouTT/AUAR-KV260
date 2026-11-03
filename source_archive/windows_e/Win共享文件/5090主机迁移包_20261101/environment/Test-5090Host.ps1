param(
    [Parameter(Mandatory=$true)][string]$VoicePython,
    [string]$ProjectRoot='E:\Win共享文件\语音共享文件',
    [switch]$TinyCudaCheck
)
$ErrorActionPreference='Stop'
if(-not (Test-Path -LiteralPath $VoicePython -PathType Leaf)){throw 'VoicePython does not exist'}
$migrationProbe=@'
import importlib.metadata as m,json,pathlib,sys
import torch
value={'python':sys.version,'executable':sys.executable,'torch':torch.__version__,
       'torch_cuda_build':torch.version.cuda,'cuda_available':torch.cuda.is_available(),
       'packages':{n:m.version(n) for n in ('omnivoice','torchaudio','transformers','numpy','soundfile')}}
if torch.cuda.is_available():
 p=torch.cuda.get_device_properties(0)
 value.update(gpu_name=p.name,gpu_memory_bytes=p.total_memory,
              compute_capability=list(torch.cuda.get_device_capability(0)),
              compiled_arch_list=torch.cuda.get_arch_list())
 if sys.argv[1]=='1':
  value['tiny_cuda_result']=float(torch.ones(1,device='cuda').sum().item())
  torch.cuda.synchronize()
print(json.dumps(value,ensure_ascii=False))
'@
& $VoicePython -I -B -X utf8 -c $migrationProbe ([int]$TinyCudaCheck.IsPresent)
if($LASTEXITCODE -ne 0){throw 'Environment check failed; do not start inference or assume old GPU calibration applies'}
$migrationTts=Join-Path $ProjectRoot 'aura\models\tts\OmniVoice'
$migrationIdentity=Get-Content -LiteralPath (Join-Path $migrationTts 'download_identity.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach($migrationItem in $migrationIdentity.files){
    $migrationFile=Join-Path $migrationTts ([string]$migrationItem.path)
    if(-not(Test-Path -LiteralPath $migrationFile -PathType Leaf)){throw ('Missing TTS model file: '+$migrationItem.path)}
    if((Get-Item -LiteralPath $migrationFile).Length -ne [long]$migrationItem.bytes){throw ('Incomplete TTS model: '+$migrationItem.path)}
}
[pscustomobject]@{ttsResource='OmniVoice';repository=$migrationIdentity.repository;revision=$migrationIdentity.revision;modelFiles='Present with expected sizes';modelsStarted=$false;deviceAccessed=$false;oldGpuCalibrationAccepted=$false}
