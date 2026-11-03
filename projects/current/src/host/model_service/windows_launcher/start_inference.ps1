param([string]$VoicePython='', [ValidateSet('Start','Status','Stop','Restart')][string]$Action='Start', [switch]$ReleaseOwnedModel)
$ErrorActionPreference='Stop'
$inferenceConfiguration=Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $PSScriptRoot 'aura/config/model_inference.local.json') | ConvertFrom-Json
$inferencePython=if($VoicePython){$VoicePython}else{[string]$inferenceConfiguration.voice_python}
if(-not (Test-Path -LiteralPath $inferencePython -PathType Leaf)){throw 'Pass the configured existing voice Python executable'}
$inferenceManager=Join-Path $PSScriptRoot 'deliverables/2026-10-30_board_owner/integration/production_model_host/manage.py'
$inferenceArguments=@('-B','-X','utf8',$inferenceManager,$Action.ToLowerInvariant())
if($ReleaseOwnedModel){$inferenceArguments+='--release-owned-model'}
& $inferencePython @inferenceArguments
if($LASTEXITCODE -ne 0){throw ('Model-only '+$Action+' failed; inspect its metadata status before retrying')}
