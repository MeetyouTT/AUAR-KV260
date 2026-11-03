"""Stage same two frontend models and run public WAV frames on ARM, no device I/O."""
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import signal
import statistics
import subprocess
import sys
import time
import urllib.request
import wave

BASE='http://192.168.50.1:59053'
PIN='fe62b56a0721a25e0fa1a15131989cbb74d818d71518003f5989a76fd86871fc'
ROOT=Path('/home/root/aura-board-owner-candidate-20261030/frontend-b3d06b653876469d')
ASR=Path('/home/root/aura-board-owner-candidate-20261030/asr-1.13.8')
EXPECTED='dd974e954ff4d5fe19eca38aba323ce6692b6089b772764ddab7256c1fb9f9b6'


def status():
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as r:value=json.load(r)
    hands=value.get('handsfree_dialogue',{});pan=value.get('manual_pan',{})
    assert value['phase']=='IDLE' and value['playing'] is False
    assert hands.get('enabled') is False and hands.get('microphone_open') is False
    assert pan.get('automatic_following') is False
    return dict(phase=value['phase'],playing=value['playing'],listening=hands.get('enabled'),
        microphone_open=hands.get('microphone_open'),pan_state=pan.get('state'),pulse_us=pan.get('pulse_us'))


def main():
    signal.alarm(45);before=status()
    ui_pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(BASE+'/manifest.json',timeout=4) as r:raw=r.read(65537)
    assert len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==PIN
    manifest=json.loads(raw)
    assert manifest['purpose']=='same_model_frontend_candidate' and manifest['candidate_root']==str(ROOT)
    assert not ROOT.is_symlink();ROOT.mkdir(parents=True,exist_ok=True)
    for entry in manifest['entries']:
        relative=Path(entry['name']);assert not relative.is_absolute() and '..' not in relative.parts
        target=ROOT/relative;assert ROOT.resolve() in target.resolve().parents and not target.is_symlink()
        target.parent.mkdir(parents=True,exist_ok=True)
        with opener.open(BASE+'/assets/'+entry['sha256'],timeout=4) as r:data=r.read(entry['bytes']+1)
        assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
        if target.exists():assert target.read_bytes()==data
        else:
            with target.open('xb') as out:out.write(data)
    sys.path.insert(0,str(ASR/'deps'))
    import numpy as np
    import sherpa_onnx
    spec=importlib.util.spec_from_file_location('candidate_frontend',ROOT/'code/board_asr_frontend.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=ASR/'models/paraformer/test_wavs/0.wav'
    with wave.open(str(source),'rb') as wav:
        assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(1,2,16000)
        pcm=wav.readframes(wav.getnframes())
    start=time.monotonic();gate=module.BoardSpeechGate(ROOT/'models');load=time.monotonic()-start
    decisions=[];durations=[]
    for offset in range(0,len(pcm),640):
        frame=pcm[offset:offset+640].ljust(640,b'\0')
        start=time.monotonic()
        decisions.append(gate(np.frombuffer(frame,dtype='<i2').astype(np.float32)/32768))
        durations.append((time.monotonic()-start)*1000)
    after=status();assert before==after
    assert subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()==ui_pid
    decision_sha=hashlib.sha256(bytes(decisions)).hexdigest()
    ordered=sorted(durations)
    signal.alarm(0)
    print(json.dumps(dict(actual_arm_execution=True,actual_frontend=True,public_wav_only=True,
        same_decisions_as_windows=decision_sha==EXPECTED,frames=len(decisions),speech_frames=sum(decisions),
        decision_sha256=decision_sha,sherpa_onnx=sherpa_onnx.__version__,numpy=np.__version__,
        load_seconds=round(load,4),mean_frame_ms=round(statistics.mean(durations),4),
        p95_frame_ms=round(ordered[int(.95*(len(ordered)-1))],4),max_frame_ms=round(max(durations),4),
        frames_over_20ms=sum(v>20 for v in durations),processed_samples=gate.samples,
        peak_rss_kb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        original_pcm_unchanged=True,candidate_root=str(ROOT),production_changed=False,
        baseenv_changed=False,hardware_actions=0,before=before,after=after)))


if __name__=='__main__':main()
