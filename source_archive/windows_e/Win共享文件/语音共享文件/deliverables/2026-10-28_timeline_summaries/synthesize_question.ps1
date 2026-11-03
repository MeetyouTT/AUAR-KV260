param([string]$Text,[string]$OutputPath)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Speech
$questionSynth=New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $questionVoice=@($questionSynth.GetInstalledVoices() | Where-Object {$_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'zh-CN'})
    if (-not $questionVoice.Count) {throw 'No installed Chinese public-test voice'}
    $questionSynth.SelectVoice($questionVoice[0].VoiceInfo.Name)
    $questionFormat=New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000,[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,[System.Speech.AudioFormat.AudioChannel]::Mono)
    $questionSynth.SetOutputToWaveFile($OutputPath,$questionFormat)
    $questionSynth.Speak($Text)
} finally {$questionSynth.Dispose()}
