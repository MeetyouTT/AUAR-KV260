"""Real production capture/ASR gate; microphone PCM stays in RAM."""
import json
from pathlib import Path
import sys
import time
import audioop

root = Path(sys.argv[1])
clip = json.loads(Path(sys.argv[2]).read_text())
sys.path.insert(0, str(root / 'aura'))
from tools.gstreamer_audio import GStreamerAudioOutput
from tools.barge_in_capture import BargeInCapture
from board.runtime.audio.barge_verify import InterruptionVerifier
from board.runtime.audio.echo_cancel import SpeexEcho

echoes = []
last_hot = [time.monotonic()]


class Echo(SpeexEcho):
    def __init__(self):
        super().__init__()
        echoes.append(self)
    def process(self, pcm):
        result = super().process(pcm)
        if audioop.rms(result, 2) >= 328:
            last_hot[0] = time.monotonic()
        return result


output = capture = None
starts = []
try:
    output = GStreamerAudioOutput(persistent=True, echo_reference=True)
    verifier = InterruptionVerifier(lambda: {'host':'192.168.50.1','port':8792}, 'echo-quiet-test')
    capture = BargeInCapture(output, echo_factory=Echo, verifier=verifier,
                            spoken_text=lambda: clip['text'])
    capture.on_speech_start = lambda: starts.append(time.monotonic())
    capture.start()
    deadline = time.monotonic()+8
    while time.monotonic()-last_hot[0] < 1 or not output.read().get('device_ready'):
        if time.monotonic() >= deadline:
            raise RuntimeError('No quiet/ready baseline; playback not started')
        if capture.snapshot()['state'] != 'RECORDING':
            raise RuntimeError('Unexpected candidate speech before quiet playback')
        time.sleep(.02)
    assert not starts, 'Speech was confirmed before the controlled playback'
    started = time.monotonic()
    output.play(clip['path'], sha256=clip['sha256'])
    while time.monotonic()-started < 9.2:
        snapshot = capture.snapshot()
        if snapshot['state'] == 'ERROR':
            raise RuntimeError(snapshot.get('error'))
        time.sleep(.02)
    snapshot = capture.snapshot()
    echo = echoes[0]
    report = {'passed':not starts and echo.reference_frames>=200 and echo.capture_frames>=200 and echo.healthy(),
              'confirmed_interruptions':len(starts), 'reference_frames':echo.reference_frames,
              'capture_frames':echo.capture_frames, 'reference_gaps':echo.reference_gaps,
              'speech_verification':snapshot['speech_verification'],
              'seconds':round(time.monotonic()-started,2), 'actual_cpu_asr_used':True,
              'actual_llm_called':False, 'microphone_audio_saved':False,
              'scope':'One controlled self-playback check; not human barge-in acceptance'}
    print('VERIFIED_PROBE '+json.dumps(report), flush=True)
finally:
    if capture: capture.close()
    if output: output.close()
