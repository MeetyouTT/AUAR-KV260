"""Actual ARM FFT candidate: same-model PCM/decisions plus segmented timings.

Isolated ORT17/source staging only; no baseenv, production or system tuning.
"""
import gc
import hashlib
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
import zipfile

BASE='http://192.168.50.1:51724'
PIN='3195f9b99b84f83045e20c85471c4952459a1f8483caeadf0b4f47e65abb0f36'
ROOT=Path('/home/root/aura-board-owner-candidate-20261030/fft-ee19b936d17aa451')
ASR=Path('/home/root/aura-board-owner-candidate-20261030/asr-1.13.8')
MODELS=Path('/home/root/aura-board-owner-candidate-20261030/frontend-b3d06b653876469d/models')
EXPECTED='dd974e954ff4d5fe19eca38aba323ce6692b6089b772764ddab7256c1fb9f9b6'


def get(path):
    with urllib.request.urlopen('http://127.0.0.1:'+path,timeout=3) as r:return json.load(r)


def safe():
    v=get('8783/api/state');h=v.get('handsfree_dialogue',{});p=v.get('manual_pan',{})
    assert v['phase']=='IDLE' and v['playing'] is False
    assert h.get('enabled') is False and h.get('microphone_open') is False
    assert p.get('automatic_following') is False


def environment():
    camera=get('8790/health')
    pid=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()
    stat=Path('/proc/'+pid+'/stat').read_text().rsplit(') ',1)[1].split()
    return dict(camera_pid=int(pid),camera_cpu_ticks=int(stat[11])+int(stat[12]),
        camera={k:camera.get(k) for k in ('capture_frames','detected_frames','last_inference_ms')},
        cpu=[int(v) for v in Path('/proc/stat').read_text().splitlines()[0].split()[1:]],
        frequency_khz={p.parent.parent.name:p.read_text().strip() for p in Path('/sys/devices/system/cpu').glob('cpu[0-9]*/cpufreq/scaling_cur_freq')},
        thermal={p.parent.name:p.read_text().strip() for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')})


def stats(values):
    order=sorted(values)
    return dict(mean=round(statistics.mean(values),4),p95=round(order[int(.95*(len(order)-1))],4),
                maximum=round(max(values),4),over_20ms=sum(v>20 for v in values))


def stage():
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(BASE+'/manifest.json',timeout=4) as r:raw=r.read(65537)
    assert len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==PIN
    manifest=json.loads(raw)
    assert manifest['purpose']=='same_model_gtcrn_fft_candidate' and manifest['candidate_root']==str(ROOT)
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
    deps=ROOT/'deps';deps.mkdir(exist_ok=True)
    for wheel in (ROOT/'wheels').glob('*.whl'):
        with zipfile.ZipFile(str(wheel)) as z:
            for item in z.infolist():
                relative=Path(item.filename);assert not relative.is_absolute() and '..' not in relative.parts
                target=deps/relative;assert deps.resolve() in target.resolve().parents and not target.is_symlink()
                assert (item.external_attr>>16)&0o170000!=0o120000
                if item.is_dir():target.mkdir(parents=True,exist_ok=True);continue
                target.parent.mkdir(parents=True,exist_ok=True);data=z.read(item)
                if target.exists():assert target.read_bytes()==data
                else:
                    with target.open('xb') as out:out.write(data)
    for relative in ('board','board/runtime','board/runtime/audio'):
        path=ROOT/'code'/relative/'__init__.py'
        if path.exists():assert path.read_bytes()==b''
        else:path.write_bytes(b'')
    sys.path[:0]=[str(ROOT/'code'),str(deps),str(ASR/'deps')]


def main():
    signal.alarm(50);safe();stage()
    import numpy as np
    import sherpa_onnx as s
    import onnxruntime as ort
    from board.runtime.audio.board_gtcrn_fft import FftGtcrnDenoiser,BoardFftSpeechGate
    source=ASR/'models/paraformer/test_wavs/0.wav'
    with wave.open(str(source),'rb') as wav:pcm=wav.readframes(wav.getnframes())
    frames=[pcm[offset:offset+640].ljust(640,b'\0') for offset in range(0,len(pcm),640)]
    config=s.OnlineSpeechDenoiserConfig(model=s.OfflineSpeechDenoiserModelConfig(
        gtcrn=s.OfflineSpeechDenoiserGtcrnModelConfig(model=str(MODELS/'gtcrn_simple.onnx')),num_threads=1,provider='cpu'))
    sdk=s.OnlineSpeechDenoiser(config);fast=FftGtcrnDenoiser(MODELS/'gtcrn_simple.onnx',profile=True)
    errors=[];error_sum=0.;count=0;max_error=0.;same_lengths=True
    for raw in frames:
        values=np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768
        expected=np.asarray(sdk(values,16000).samples,dtype=np.float32);actual=fast(values).samples
        same_lengths=same_lengths and len(expected)==len(actual)
        assert len(expected)==len(actual)
        if len(actual):
            delta=expected.astype(np.float64)-actual.astype(np.float64)
            error_sum+=float(np.dot(delta,delta));count+=len(delta)
            max_error=max(max_error,float(np.max(np.abs(delta))))
    expected=np.asarray(sdk.flush().samples,dtype=np.float32);actual=fast.flush().samples
    assert len(expected)==len(actual)
    delta=expected.astype(np.float64)-actual.astype(np.float64)
    error_sum+=float(np.dot(delta,delta));count+=len(delta)
    max_error=max(max_error,float(np.max(np.abs(delta))) if len(delta) else 0.)
    comparison=dict(samples=count,max_abs_float_error=max_error,rms_float_error=(error_sum/max(count,1))**.5,
                    same_segment_lengths=same_lengths,flush_samples=len(actual))
    assert max_error<=1e-4 and comparison['rms_float_error']<=1e-5
    del sdk,fast;gc.collect()
    results=[]
    for threads in (1,2):
        before=environment();load_at=time.monotonic();gate=BoardFftSpeechGate(MODELS,num_threads=threads,profile=True)
        load=time.monotonic()-load_at
        cpu=time.process_time();start=time.monotonic();durations=[];decisions=[]
        totals=dict(fft_ms=0.,ort_ms=0.,ifft_ola_ms=0.)
        for raw in frames:
            values=np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768
            began=time.monotonic();decisions.append(gate(values));durations.append((time.monotonic()-began)*1000)
            for key in totals:totals[key]+=gate.denoiser.last_timing[key]
        wall=time.monotonic()-start;cpu=time.process_time()-cpu;after=environment();safe()
        digest=hashlib.sha256(bytes(decisions)).hexdigest()
        results.append(dict(threads=threads,load_seconds=round(load,4),wall_seconds=round(wall,4),
            process_cpu_percent_one_core=round(cpu/wall*100,2),total_frame_ms=stats(durations),
            actual_fast_path_stage_mean_ms={key:round(value/len(frames),4) for key,value in totals.items()},
            same_decisions_as_sdk=digest==EXPECTED,decision_sha256=digest,speech_frames=sum(decisions),
            before=before,after=after,peak_rss_kb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
        del gate;gc.collect()
    signal.alarm(0)
    print(json.dumps(dict(candidate_root=str(ROOT),actual_arm_execution=True,same_model=True,
        isolated_ort=ort.__version__,numpy=np.__version__,sherpa=s.__version__,pcm_comparison=comparison,
        results=results,production_changed=False,baseenv_changed=False,hardware_actions=0,system_tuning=False)))


if __name__=='__main__':main()
