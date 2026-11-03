param([ValidateSet('On','Off','Status')][string]$Mode='Status')
$ErrorActionPreference='Stop'
& 'D:\AURARuntimes\voice-py310\Scripts\python.exe' -B -X utf8 (Join-Path $PSScriptRoot 'manage_thinking_test.py') $Mode.ToLowerInvariant()
if($LASTEXITCODE -ne 0){throw 'Thinking test operation failed; inspect its recorded result before retrying'}
