$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Speech
$wakeSynth=New-Object System.Speech.Synthesis.SpeechSynthesizer
$wakeSynth.SelectVoice('Microsoft Huihui Desktop')
$wakeFormat=New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000,[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,[System.Speech.AudioFormat.AudioChannel]::Mono)
$wakePhrases=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'wake_phrases.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$wakeDirectory=Join-Path $PSScriptRoot 'synthetic_wake_fixtures'
New-Item -ItemType Directory -Path $wakeDirectory -Force | Out-Null
try {
 foreach ($wakePhrase in $wakePhrases) {
  $wakeSynth.SetOutputToWaveFile((Join-Path $wakeDirectory ($wakePhrase.id+'.wav')),$wakeFormat)
  $wakeSynth.Speak([string]$wakePhrase.text)
  $wakeSynth.SetOutputToNull()
 }
} finally {$wakeSynth.Dispose()}
Write-Output 'Synthetic fixtures written; no speaker playback.'
