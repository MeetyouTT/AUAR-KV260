param(
    [Parameter(Mandatory=$true)][string]$BasePython,
    [string]$RuntimeRoot='D:\AURARuntimes\voice-py310'
)
$ErrorActionPreference='Stop'
if(-not (Test-Path -LiteralPath $BasePython -PathType Leaf)){throw 'Specify an installed Python 3.10 interpreter'}
& $BasePython -I -B -c 'import sys; assert sys.version_info[:2]==(3,10), "Use Python 3.10 for the recorded voice environment"'
if($LASTEXITCODE -ne 0){throw 'Base Python version check failed'}
if(Test-Path -LiteralPath $RuntimeRoot){throw 'RuntimeRoot already exists. Inspect it; this script does not overwrite environments.'}
& $BasePython -m venv $RuntimeRoot
if($LASTEXITCODE -ne 0){throw 'venv creation failed'}
$migrationPython=Join-Path $RuntimeRoot 'Scripts\python.exe'
$migrationRequirements=Join-Path $PSScriptRoot 'voice_py310_requirements_effective.txt'
if(-not (Test-Path -LiteralPath $migrationRequirements)){throw 'Observed package lock is missing'}
# These are recorded source-host versions, not an assertion of 5090 compatibility.
& $migrationPython -m pip install --extra-index-url 'https://download.pytorch.org/whl/cu128' --find-links (Join-Path $PSScriptRoot 'wheels') -r $migrationRequirements
if($LASTEXITCODE -ne 0){throw 'Recorded dependency install failed; preserve logs and resolve deliberately on the new host'}
$migrationSource=Join-Path (Split-Path $PSScriptRoot -Parent) 'external_dependencies\source'
if(Test-Path -LiteralPath (Join-Path $migrationSource 'pyproject.toml')){
    & $migrationPython -m pip install --no-deps --no-build-isolation $migrationSource
    if($LASTEXITCODE -ne 0){throw 'Preserved OmniVoice source install failed'}
}
& (Join-Path $PSScriptRoot 'Test-5090Host.ps1') -VoicePython $migrationPython -TinyCudaCheck
if($LASTEXITCODE -ne 0){throw 'New runtime verification failed'}
Write-Output ('Voice runtime prepared at '+$migrationPython+'. No project configuration changed and no model server started.')
