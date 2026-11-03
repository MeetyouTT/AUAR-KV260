"""Bounded real microphone tests; camera/UI/FPGA configuration is preserved."""
import array
import base64
import glob
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import wave

release = Path('/home/root/aura-audio-capture-20261015/releases/9a829a5e2472ec17')
sys.path.insert(0, str(release/'aura'))
from board.runtime.audio.capture import Mcp01Capture
from tools.board_audio_capture import playback_active


def health():
    with urllib.request.urlopen('http://127.0.0.1:8790/health', timeout=3) as response:
        return json.load(response)


def services():
    return subprocess.check_output(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service',
        '-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'], text=True)


def wait_samples(capture):
    deadline = time.monotonic()+3
    while capture.snapshot()['sample_count'] < 2048 and time.monotonic() < deadline:
        assert capture.snapshot()['state'] == 'RECORDING', capture.snapshot()
        time.sleep(.03)
    assert capture.snapshot()['sample_count'] >= 2048, capture.snapshot()


before = health()
before_services = services()
assert playback_active() is False
output = release/('acceptance-'+str(time.monotonic_ns()))
output.mkdir(mode=0o700)
wav_path = output/'mcp01-3s.wav'
p = subprocess.run(['python3','-B',str(release/'aura/tools/board_audio_capture.py'),
    '--seconds','3','--output',str(wav_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, timeout=9)
assert p.returncode == 0, (p.returncode, p.stderr)
natural = json.loads(p.stdout)
blob = wav_path.read_bytes()
with wave.open(io.BytesIO(blob),'rb') as wav:
    assert (wav.getframerate(),wav.getnchannels(),wav.getsampwidth()) == (16000,1,2)
    assert wav.getnframes() == natural['sample_count'] == 48000
    pcm = wav.readframes(wav.getnframes())
assert hashlib.sha256(pcm).hexdigest() == natural['pcm_sha256']
samples = array.array('h', pcm)
if sys.byteorder != 'little':
    samples.byteswap()
energy = {'peak_pcm16': max(abs(x) for x in samples),
          'rms_pcm16': round(math.sqrt(sum(x*x for x in samples)/len(samples)),3),
          'nonzero_samples': sum(x!=0 for x in samples)}
with Mcp01Capture(playback_active, max_seconds=5) as capture:
    capture.start()
    wait_samples(capture)
    with Mcp01Capture(playback_active, max_seconds=3) as other:
        try:
            other.start()
        except RuntimeError as exc:
            assert 'already owned' in str(exc), str(exc)
            exclusive = True
        else:
            raise AssertionError('Second capture owner accepted')
    stopped = capture.stop()
    assert 1600 <= stopped.audio.sample_count < 80000
    assert capture._process is None
    stopped_meta = capture.take().metadata()
with Mcp01Capture(playback_active, max_seconds=3) as capture:
    capture.start()
    wait_samples(capture)
    capture.cancel()
    assert capture.snapshot()['state']=='CANCELLED' and not capture.snapshot()['has_result']
    assert capture._process is None
    try:
        capture.take()
    except RuntimeError:
        cancelled = True
    else:
        raise AssertionError('Cancelled audio was delivered')
after = health()
after_services = services()
assert before_services == after_services
assert before['board_boot_id'] == after['board_boot_id']
assert before['service_epoch'] == after['service_epoch']
assert after['capture_frames'] > before['capture_frames']
assert after['detected_frames'] > before['detected_frames']
assert not any(after[key] for key in ('camera_error','detector_error','preview_error'))
owners = subprocess.run(['fuser']+glob.glob('/dev/snd/pcm*'),
                        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=3)
assert owners.returncode == 1, owners.stdout
result = {'passed':True,'scope':'REAL_MCP01_CAPTURE_STOP_CANCEL_WITH_LIVE_VISION',
    'board_output':str(output),'natural_capture':natural,'energy':energy,'early_stop':stopped_meta,
    'exclusive_owner_rejected':exclusive,'cancelled_audio_not_delivered':cancelled,
    'sound_owners_after':owners.stdout,'services_unchanged':True,
    'camera_before':before,'camera_after':after,
    'artifacts':{'mcp01-3s.wav':{'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),
        'base64':base64.b64encode(blob).decode()}},
    'not_tested':['physical_speech_intelligibility','ASR','LAN','dynamic_reply','UI_record_button']}
(output/'acceptance.json').write_text(json.dumps({k:v for k,v in result.items() if k!='artifacts'},indent=2))
print(json.dumps(result,ensure_ascii=False))
