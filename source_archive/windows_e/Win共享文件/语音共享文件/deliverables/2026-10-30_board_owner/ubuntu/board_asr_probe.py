"""Actual same-model public WAV ASR on ARM, without capture or playback."""
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import urllib.request
import wave

ROOT=Path('/home/root/aura-board-owner-candidate-20261030/asr-1.13.8')
MODEL='f36a0433bcf096bd6d6f11b80a3ac8bed110bdca632fe0d731df8d1a84475945'
TOKENS='59aba8873a2ed1e122c25fee421e25f283b63290efbde85c1f01a853d83cb6e6'


def get(path):
    with urllib.request.urlopen('http://127.0.0.1:'+path,timeout=3) as response:return json.load(response)


def state():
    value=get('8783/api/state');hands=value.get('handsfree_dialogue',{});pan=value.get('manual_pan',{})
    assert value['phase']=='IDLE' and not value['playing']
    assert hands.get('enabled') is False and hands.get('microphone_open') is False
    assert pan.get('automatic_following') is False
    return dict(phase=value['phase'],playing=value['playing'],listening=hands.get('enabled'),
                microphone_open=hands.get('microphone_open'),pan_state=pan.get('state'),pulse_us=pan.get('pulse_us'))


def main():
    signal.alarm(50)
    before=state()
    available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                       if line.startswith('MemAvailable:')))
    assert available>1500000,'Not enough headroom for isolated same-model ASR probe'
    ui_pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
    camera_pid=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()
    argv=Path('/proc/'+ui_pid+'/cmdline').read_bytes().decode().rstrip('\0').split('\0')
    config=json.loads(Path(argv[argv.index('--config')+1]).read_text())
    actual=Path(config['runtime'])/'aura'
    source_hashes={relative:hashlib.sha256((actual/relative).read_bytes()).hexdigest() for relative in
                   ('tools/board_avatar_gtk.py','board/runtime/audio/channel_jobs.py','board/vision/ui_camera_service.py')}
    sys.path.insert(0,str(ROOT/'deps'))
    import sherpa_onnx
    import numpy
    path=ROOT/'code/board/runtime/audio/board_asr.py'
    spec=importlib.util.spec_from_file_location('candidate_board_asr',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with wave.open(str(ROOT/'models/paraformer/test_wavs/0.wav'),'rb') as wav:
        assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(1,2,16000)
        pcm=wav.readframes(wav.getnframes())
    start=time.monotonic()
    decoder=module.BoardParaformer(ROOT/'models/paraformer',model_sha256=MODEL,tokens_sha256=TOKENS)
    load_seconds=time.monotonic()-start
    runs=[]
    for index in range(2):
        start=time.monotonic()
        text=decoder.transcribe(pcm,deadline=start+20)
        elapsed=time.monotonic()-start
        assert text
        runs.append(dict(run=index+1,text=text,seconds=round(elapsed,4),rtf=round(elapsed/(len(pcm)/32000),4)))
    after=state()
    assert before==after
    for name,expected in (('aura-avatar-ui.service',ui_pid),('aura-camera-ui.service',camera_pid)):
        assert subprocess.check_output(['systemctl','show',name,'-p','MainPID','--value'],text=True).strip()==expected
    signal.alarm(0)
    print(json.dumps(dict(actual_arm_asr=True,source='existing_upstream_public_test_wavs/0.wav',
        model_sha256=MODEL,tokens_sha256=TOKENS,model_unchanged=True,
        candidate_root=str(ROOT),sherpa_onnx=sherpa_onnx.__version__,numpy=numpy.__version__,
        load_seconds=round(load_seconds,4),audio_seconds=round(len(pcm)/32000,4),runs=runs,
        peak_rss_kb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        available_before_kb=available,source_hashes=source_hashes,ui_pid=int(ui_pid),camera_pid=int(camera_pid),
        hardware_actions=0,baseenv_changed=False,production_changed=False,before=before,after=after),ensure_ascii=True))


if __name__=='__main__':main()
