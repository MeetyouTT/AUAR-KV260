"""Read-only bounded kernel/thread profiling on existing isolated public assets.

No sysfs writes, scheduling/affinity changes, service changes or device I/O.
GTCRN call time includes its private C++ STFT/ORT/ISTFT implementation; the
separate NumPy FFT microbenchmark is explicitly only a proxy, not that path.
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

MODE='gtcrn_only'
CASES=[(1,1),(2,1)]
ASR=Path('/home/root/aura-board-owner-candidate-20261030/asr-1.13.8')
MODELROOT=Path('/home/root/aura-board-owner-candidate-20261030/frontend-b3d06b653876469d/models')


def request(path):
    with urllib.request.urlopen('http://127.0.0.1:'+path,timeout=3) as r:return json.load(r)


def safe():
    value=request('8783/api/state');hands=value.get('handsfree_dialogue',{});pan=value.get('manual_pan',{})
    assert value['phase']=='IDLE' and value['playing'] is False
    assert hands.get('enabled') is False and hands.get('microphone_open') is False
    assert pan.get('automatic_following') is False


def host():
    freq={str(p):p.read_text().strip() for p in Path('/sys/devices/system/cpu').glob('cpu[0-9]*/cpufreq/scaling_cur_freq')}
    thermal={}
    for p in Path('/sys/class/thermal').glob('thermal_zone*'):
        try:thermal[p.name]=dict(type=(p/'type').read_text().strip(),temp=(p/'temp').read_text().strip())
        except OSError:pass
    camera=request('8790/health')
    pid=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()
    stat=Path('/proc/'+pid+'/stat').read_text().rsplit(') ',1)[1].split()
    return dict(cpu_frequency_khz=freq,thermal=thermal,
        cpu=[int(v) for v in Path('/proc/stat').read_text().splitlines()[0].split()[1:]],
        camera={k:camera.get(k) for k in ('capture_frames','detected_frames','capture_hz','detection_hz','last_inference_ms')},
        camera_pid=int(pid),camera_cpu_ticks=int(stat[11])+int(stat[12]),loadavg=Path('/proc/loadavg').read_text().strip())


def stats(values):
    ordered=sorted(values)
    return dict(mean=round(statistics.mean(values),4),p95=round(ordered[int(.95*(len(ordered)-1))],4),
                maximum=round(max(values),4),over_20ms=sum(v>20 for v in values))


def run(s,np,frames,gt,vt):
    safe();start_load=time.monotonic();denoiser=vad=None
    if MODE!='vad_only':
        config=s.OnlineSpeechDenoiserConfig(model=s.OfflineSpeechDenoiserModelConfig(
            gtcrn=s.OfflineSpeechDenoiserGtcrnModelConfig(model=str(MODELROOT/'gtcrn_simple.onnx')),
            num_threads=gt,provider='cpu'))
        assert config.validate();denoiser=s.OnlineSpeechDenoiser(config)
    if MODE!='gtcrn_only':
        vc=s.VadModelConfig();vc.silero_vad.model=str(MODELROOT/'silero_vad_v5.onnx')
        vc.silero_vad.threshold=.5;vc.silero_vad.min_speech_duration=0.;vc.silero_vad.min_silence_duration=0.
        vc.silero_vad.max_speech_duration=19.;vc.num_threads=vt;vc.sample_rate=16000
        vad=s.VoiceActivityDetector(vc,buffer_size_in_seconds=22)
    zero=np.zeros(320,dtype=np.float32)
    for _ in range(32):
        values=denoiser(zero,16000).samples if denoiser else zero
        if vad and len(values):vad.accept_waveform(values)
        if vad:
            while not vad.empty():vad.pop()
    if denoiser:denoiser.reset()
    if vad:vad.reset()
    load=time.monotonic()-start_load;before=host();start=time.monotonic();cpu=time.process_time()
    conversion=[];kernel=[];output_copy=[];vadtime=[];totals=[];decisions=[];output_hash=hashlib.sha256();processed=0
    for raw in frames:
        t0=time.monotonic()
        values=np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768
        # The wrapper's round trip preserves current PCM16 decision semantics.
        raw2=np.rint(values*32768).clip(-32768,32767).astype('<i2').tobytes()
        values=np.frombuffer(raw2,dtype='<i2').astype(np.float32)/32768
        t1=time.monotonic()
        output=denoiser(values,16000) if denoiser else None
        t2=time.monotonic()
        clean=output.samples if output else values
        t2b=time.monotonic()
        if vad:
            if len(clean):vad.accept_waveform(clean)
            decisions.append(bool(vad.is_speech_detected()))
            while not vad.empty():vad.pop()
        t3=time.monotonic()
        processed+=len(clean);output_hash.update(np.asarray(clean,dtype=np.float32).tobytes())
        conversion.append((t1-t0)*1000);kernel.append((t2-t1)*1000)
        output_copy.append((t2b-t2)*1000);vadtime.append((t3-t2b)*1000);totals.append((t3-t0)*1000)
    elapsed=time.monotonic()-start;cpu=time.process_time()-cpu;after=host();safe()
    result=dict(mode=MODE,gtcrn_threads=gt,vad_threads=vt,frames=len(frames),load_seconds=round(load,4),
        wall_seconds=round(elapsed,4),process_cpu_seconds=round(cpu,4),process_cpu_percent_one_core=round(cpu/elapsed*100,2),
        conversion_ms=stats(conversion),gtcrn_stft_ort_istft_ms=stats(kernel),output_list_ms=stats(output_copy),
        vad_ms=stats(vadtime),total_ms=stats(totals),
        output_float32_sha256=output_hash.hexdigest(),processed_samples=processed,
        decision_sha256=hashlib.sha256(bytes(decisions)).hexdigest() if vad else None,
        speech_frames=sum(decisions) if vad else None,before=before,after=after,
        peak_rss_kb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    del denoiser,vad;gc.collect()
    return result


def main():
    signal.alarm(50);safe();sys.path.insert(0,str(ASR/'deps'))
    import numpy as np
    import sherpa_onnx as s
    with wave.open(str(ASR/'models/paraformer/test_wavs/0.wav'),'rb') as wav:pcm=wav.readframes(wav.getnframes())
    frames=[pcm[offset:offset+640].ljust(640,b'\0') for offset in range(0,len(pcm),640)]
    results=[run(s,np,frames,gt,vt) for gt,vt in CASES]
    # The child uses the original board Python path rather than candidate deps.
    code=("import onnxruntime as o,json;v=o.SessionOptions();v.intra_op_num_threads=1;"
          "s=o.InferenceSession(%r,sess_options=v,providers=['CPUExecutionProvider']);"
          "print(json.dumps(dict(version=o.__version__,metadata=s.get_modelmeta().custom_metadata_map,"
          "inputs=[dict(name=i.name,shape=i.shape,type=i.type) for i in s.get_inputs()])))" %
          str(MODELROOT/'gtcrn_simple.onnx'))
    child=subprocess.run([sys.executable,'-B','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
    original_ort=dict(exit_code=child.returncode)
    if child.returncode==0:original_ort.update(json.loads(child.stdout))
    else:original_ort['diagnostic']=child.stderr.decode('utf-8','replace')[-1000:]
    # Explicitly not the private C++ FFT. This only bounds Python NumPy FFT work.
    start=time.monotonic();values=np.zeros(512,dtype=np.float32)
    for _ in range(1000):np.fft.irfft(np.fft.rfft(values),n=512)
    proxy=(time.monotonic()-start)*1000/1000
    signal.alarm(0)
    print(json.dumps(dict(results=results,original_board_ort=original_ort,numpy_fft512_pair_proxy_ms=round(proxy,4),
        fft_proxy_is_actual_sherpa_fft=False,production_changed=False,hardware_actions=0,
        system_tuning=False,public_wav_only=True)))


if __name__=='__main__':main()
