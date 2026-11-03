"""Offline public-audio comparison. Never opens a microphone or calls a service."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import socket
import statistics
import sys
import time
import wave

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(PROJECT / 'aura'))
from board.runtime.audio.automatic_capture import SpeechEndpoint
from board.runtime.audio.silero_gate import SileroFrameGate

EXTERNAL = Path('D:/AIModels/audio-frontend-eval-20261021')
RATE = 16000


def load(path):
    with wave.open(str(path)) as audio:
        assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (1, 2, RATE)
        return np.frombuffer(audio.readframes(audio.getnframes()), dtype='<i2').astype(np.float32)/32768


def pcm(samples):
    return np.rint(np.clip(samples, -1., 32767/32768)*32768).astype('<i2').tobytes()


def level(samples, rms):
    value = np.sqrt(np.mean(samples.astype(np.float64)**2))
    return (samples * (rms/max(value, 1.e-12))).astype(np.float32)


def make_cases():
    rng = np.random.default_rng(211021)
    sources = []
    cases = []
    count = 12*RATE
    white = rng.normal(size=count).astype(np.float32)
    filtered = np.convolve(white, np.ones(33)/33, mode='same').astype(np.float32)
    t = np.arange(count)/RATE
    noises = {
        'digital_silence': np.zeros(count, dtype=np.float32),
        'generated_white': level(white, .03),
        'generated_lowpass': level(filtered, .03),
        'generated_harmonic_fan_like': level((filtered+.1*np.sin(2*np.pi*120*t)+.05*np.sin(2*np.pi*240*t)).astype(np.float32), .03),
        'generated_am_rustle_like': level(white*(.05+np.sin(2*np.pi*.7*t)**4), .035),
    }
    for name, x in noises.items():
        cases.append({'name':name, 'samples':x, 'expected':'non_speech', 'source':'Deterministic generated stress signal, not a room recording.'})
    paths = [Path('D:/AIModels/speaker-identity/public-samples')/f'spk{s}_snt{n}.wav' for s in (1,2) for n in (1,2)]
    paths += [PROJECT / f'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/{n}.wav' for n in (0,1,2)]
    for index, path in enumerate(paths):
        raw = load(path)
        # Bound individual samples to the existing capture budget; never use private recordings.
        if len(raw) > 16*RATE:
            raw = raw[:16*RATE]
        sources.append({'id':f'public_{index}', 'path':str(path), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                        'seconds_used':len(raw)/RATE, 'scope':'Upstream public test sample; not user enrollment.'})
        speech = level(raw, .04)
        pad = lambda x: np.concatenate((np.zeros(8000,dtype=np.float32),x,np.zeros(17600,dtype=np.float32)))
        variants = [('clean', speech), ('quiet', level(raw,.004))]
        for snr in (5, 0):
            noise = level(np.resize(noises['generated_harmonic_fan_like'],len(raw)), .04/(10**(snr/20)))
            variants.append((f'fan_like_snr{snr}',speech+noise))
        for name,x in variants:
            cases.append({'name':f'public_{index}_{name}', 'samples':pad(x), 'expected':'speech',
                          'source':f'public_{index}', 'speech_interval_samples':[8000,8000+len(raw)]})
    for name in ('speech_with_noise.wav','inp_16k.wav'):
        path = EXTERNAL/name
        raw = load(path)
        cases.append({'name':'upstream_'+path.stem,'samples':np.concatenate((raw,np.zeros(17600,dtype=np.float32))),
                      'expected':'speech','source':str(path)})
    return cases, sources


def evaluate(samples, gate=None):
    endpoint = SpeechEndpoint(20, frame_classifier=gate)
    starts = []; segments = []; timings = []
    position = 0
    p = pcm(samples)
    for i in range(0,len(p)-639,640):
        before = endpoint.active
        began = time.perf_counter()
        result = endpoint.feed(p[i:i+640])
        timings.append((time.perf_counter()-began)*1000)
        position += 320
        if endpoint.active and not before:
            starts.append(position/RATE)
        if result is not None:
            start = position-len(result)//2
            # The complete result must be an exact slice of original PCM: no denoising or dropped prefix.
            assert result == p[start*2:position*2]
            segments.append([start/RATE,position/RATE])
            endpoint = SpeechEndpoint(20, frame_classifier=gate)
    t = sorted(timings)
    return {'speech_starts':starts, 'segments':segments, 'still_active_at_end':endpoint.active,
            'calls':len(t), 'feed_ms_median':statistics.median(t), 'feed_ms_p95':t[int(.95*(len(t)-1))],
            'feed_ms_max':max(t), 'feed_real_time_factor':sum(t)/(position/RATE*1000),
            'pcm_slice_exact':True, 'gate':gate.public() if gate else None}


def denoise_cases(cases):
    import sherpa_onnx as s
    config = s.OnlineSpeechDenoiserConfig(model=s.OfflineSpeechDenoiserModelConfig(
        gtcrn=s.OfflineSpeechDenoiserGtcrnModelConfig(model=str(EXTERNAL/'gtcrn_simple.onnx')),
        num_threads=1, provider='cpu'))
    assert config.validate()
    rows=[]
    for case in cases:
        denoiser = s.OnlineSpeechDenoiser(config)
        size = denoiser.frame_shift_in_samples
        chunks=[];calls=[];produced_at=None
        for start in range(0,len(case['samples']),size):
            began=time.perf_counter()
            out=denoiser(case['samples'][start:start+size],RATE)
            calls.append((time.perf_counter()-began)*1000)
            values=np.asarray(out.samples,dtype=np.float32)
            if len(values) and produced_at is None:produced_at=min(start+size,len(case['samples']))
            chunks.append(values)
        chunks.append(np.asarray(denoiser.flush().samples,dtype=np.float32))
        enhanced=np.concatenate(chunks)
        assert len(enhanced)==len(case['samples']) and np.isfinite(enhanced).all()
        row={'name':case['name'],'hop_samples':size,'first_output_after_input_samples':produced_at,
             'processing_rtf':sum(calls)/(len(enhanced)/RATE*1000),
             'process_ms_p95':float(np.percentile(calls,95)),
             'input_samples':len(enhanced),'output_samples':len(enhanced),
             'original_rms':float(np.sqrt(np.mean(case['samples']**2))),
             'enhanced_rms':float(np.sqrt(np.mean(enhanced**2))),
             'silero_after':evaluate(enhanced,SileroFrameGate(EXTERNAL/'silero_vad.int8.onnx')),
             'silero_v5_after':evaluate(enhanced,SileroFrameGate(EXTERNAL/'silero_vad_v5.onnx')),
             'warning':'RMS reduction is not proof of improved target speech or transcription.'}
        output=EXTERNAL/'derived'/('gtcrn_'+case['name']+'.wav')
        output.parent.mkdir(exist_ok=True)
        with wave.open(str(output),'wb') as audio:
            audio.setparams((1,2,RATE,0,'NONE','not compressed'));audio.writeframes(pcm(enhanced))
        row['enhanced_path']=str(output)
        rows.append(row)
    return rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--denoise',action='store_true');args=parser.parse_args()
    # Models and data have already been provisioned; any network access now is a test failure.
    def blocked(*a,**kw): raise RuntimeError('Network forbidden during offline evaluation')
    socket.socket.connect=blocked
    cases,sources=make_cases()
    rows=[]
    for case in cases:
        results={}
        for name in ('energy','silero_vad.int8.onnx','silero_vad.onnx','silero_vad_v5.onnx'):
            gate=None if name=='energy' else SileroFrameGate(EXTERNAL/name)
            results[name]=evaluate(case['samples'],gate)
        rows.append({k:v for k,v in case.items() if k!='samples'} | {'seconds':len(case['samples'])/RATE,'results':results})
        print(json.dumps({'case':case['name'],'starts':{k:len(v['speech_starts']) for k,v in results.items()}}),flush=True)
    report={'date':'2026-10-21','production_changed':False,'network_blocked':True,
            'microphone_opened':False,'samples':sources,'cases':rows,
            'versions':{name:importlib.metadata.version(name) for name in ('numpy','onnxruntime','sherpa-onnx')},
            'limits':'Small public/generated evaluation, not room noise, television rejection, or human acceptance.'}
    if (HERE/'pc_benchmark.json').exists() and not (HERE/'pc_benchmark_v4.json').exists():
        (HERE/'pc_benchmark_v4.json').write_bytes((HERE/'pc_benchmark.json').read_bytes())
    (HERE/'pc_benchmark.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.denoise:
        selected=[c for c in cases if c['expected']=='non_speech' or any(c['name'].startswith(f'public_{n}_') for n in (4,5,6))
                  or c['name'].startswith('upstream_')]
        report['gtcrn']=denoise_cases(selected)
    (HERE/'pc_benchmark.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(rows),'denoise_cases':len(report.get('gtcrn',[])), 'status':'OFFLINE_EVALUATION_COMPLETE'}))


if __name__=='__main__':main()
