"""Fixed public WAV, CPU-only numerical and bounded Windows timing comparison.

Not an ARM or realtime result. No ASR, microphone, playback, model host, GPU or
production data is used. Only the already pinned GTCRN/Silero resources are read.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import wave


def stats(values):
    rows = sorted(values)
    return dict(mean=sum(rows)/len(rows),p95=rows[int(.95*(len(rows)-1))],maximum=max(rows))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code-root',type=Path,required=True)
    parser.add_argument('--models-root',type=Path,required=True)
    parser.add_argument('--public-wav',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--runs',type=int,choices=(1,2,3),default=3)
    args = parser.parse_args(argv)
    sys.path.insert(0,str(args.code_root))
    import numpy as np
    import onnxruntime as ort
    import sherpa_onnx as sherpa
    import board.runtime.audio.board_gtcrn_fft as base
    from board.runtime.audio.automatic_capture import SpeechEndpoint
    from board.runtime.audio.board_capture import BoardFrontendPool
    source = Path(__file__).parent/'candidate/board_gtcrn_reuse.py'
    spec = importlib.util.spec_from_file_location('isolated_gtcrn_reuse',source)
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    candidate.verify_baseline()
    if hashlib.sha256(args.public_wav.read_bytes()).hexdigest() != '1a6bf94091d9c35e11aea5d494d05e3287b8f5c767f6de3bfd796d91b637500c':
        raise ValueError('Use only the already pinned public upstream WAV')
    with wave.open(str(args.public_wav),'rb') as wav:
        if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate()) != (1,2,16000):
            raise ValueError('Pinned public WAV format changed')
        pcm = wav.readframes(wav.getnframes())
    audio = np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768
    modes = [('baseline',False,False),('reuse',True,False),('io',False,True),('combined',True,True)]
    records,reference,reference_vad,reference_endpoint = [],None,None,None
    for mode,reuse,binding in modes:
        if mode == 'baseline':
            denoiser = base.FftGtcrnDenoiser(args.models_root/'gtcrn_simple.onnx',num_threads=1,profile=True)
            gate = base.BoardFftSpeechGate(args.models_root,num_threads=1)
        else:
            denoiser = candidate.ReuseFftGtcrnDenoiser(args.models_root/'gtcrn_simple.onnx',num_threads=1,
                profile=True,buffer_reuse=reuse,io_binding=binding)
            gate = candidate.ReuseFftSpeechGate(args.models_root,num_threads=1,
                buffer_reuse=reuse,io_binding=binding)
        for _ in range(32):
            denoiser(np.zeros(320,dtype=np.float32))
        runs = []
        for index in range(args.runs):
            denoiser.reset()
            actual,ms = [],[]
            stages = dict(fft_ms=0.,ort_ms=0.,ifft_ola_ms=0.)
            began = time.perf_counter()
            for offset in range(0,len(audio),320):
                at = time.perf_counter()
                actual.append(denoiser(audio[offset:offset+320]).samples)
                ms.append((time.perf_counter()-at)*1000)
                for key in stages:
                    stages[key] += denoiser.last_timing[key]
            actual.append(denoiser.flush().samples)
            elapsed = time.perf_counter()-began
            actual = np.concatenate(actual)
            if reference is None:
                reference = actual.copy()
            delta = actual.astype(np.float64)-reference.astype(np.float64)
            maximum = float(np.max(np.abs(delta)))
            rms = float(np.sqrt(np.mean(delta*delta)))
            if len(actual) != len(audio) or maximum>1e-4 or rms>1e-5:
                raise ValueError('Candidate PCM equivalence failed')
            runs.append(dict(run=index+1,wall_seconds=elapsed,frame_ms=stats(ms),
                denoiser_stage_total_ms=stages,max_abs_error=maximum,rms_error=rms,
                pcm16_equal_fraction=float(np.mean(np.rint(actual*32768).clip(-32768,32767) ==
                                                  np.rint(reference*32768).clip(-32768,32767)))))
        pool = BoardFrontendPool(gate)
        lease = pool.acquire()
        vad = []
        for offset in range(0,len(pcm),640):
            raw = pcm[offset:offset+640].ljust(640,b'\0')
            vad.append(bool(lease(np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768)))
        lease.close()
        endpoint = SpeechEndpoint(frame_classifier=pool.acquire(),pre_roll_ms=500)
        padded,result = pcm+bytes(48000),None
        for offset in range(0,len(padded),640):
            result = endpoint.feed(padded[offset:offset+640].ljust(640,b'\0'))
            if result is not None:
                break
        endpoint.frame_classifier.close()
        pool.close()
        if not result:
            raise ValueError('Public endpoint did not complete')
        if reference_vad is None:
            reference_vad,reference_endpoint = vad,result
        if vad != reference_vad or result != reference_endpoint:
            raise ValueError('Candidate VAD/original endpoint PCM changed')
        records.append(dict(mode=mode,buffer_reuse=reuse,cpu_io_binding=binding,runs=runs,
            vad_decision_sha256=hashlib.sha256(bytes(vad)).hexdigest(),
            same_vad_decisions=True,same_original_endpoint_pcm=True,
            endpoint_samples=len(result)//2,endpoint_sha256=hashlib.sha256(result).hexdigest()))
        del denoiser,gate,pool,endpoint,lease
    report = dict(status='WINDOWS_PUBLIC_CPU_COMPARISON_ONLY',ort=ort.__version__,numpy=np.__version__,
        sherpa=sherpa.__version__,provider='CPUExecutionProvider',num_threads=1,
        public_wav_sha256=hashlib.sha256(args.public_wav.read_bytes()).hexdigest(),
        baseline_sha256=candidate.BASELINE_SHA256,frontend_sha256=candidate.FRONTEND_SHA256,
        candidate_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),records=records,
        real_arm_execution=False,production_changed=False,microphone_or_playback=False,
        gpu_inference=False,conclusion='Host CPU numbers do not establish ARM or whole-system benefit')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(status=report['status'],modes=[dict(mode=r['mode'],
        means=[round(v['frame_ms']['mean'],4) for v in r['runs']],
        max_error=max(v['max_abs_error'] for v in r['runs']),
        pcm16_equal=min(v['pcm16_equal_fraction'] for v in r['runs']),
        same_vad=r['same_vad_decisions'],same_endpoint=r['same_original_endpoint_pcm']) for r in records])))


if __name__ == '__main__':
    main()
