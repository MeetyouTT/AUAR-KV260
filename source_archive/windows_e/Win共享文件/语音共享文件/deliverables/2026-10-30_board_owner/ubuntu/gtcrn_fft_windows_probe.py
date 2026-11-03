"""Same-model SDK/FFT public PCM, VAD endpoint and ASR comparison on Windows."""
import hashlib
import json
from pathlib import Path
import sys
import time
import wave

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
sys.path.insert(0,str(PROJECT/'aura'))


def main():
    import numpy as np
    import sherpa_onnx as s
    from board.runtime.audio.board_gtcrn_fft import FftGtcrnDenoiser,BoardFftSpeechGate
    from board.runtime.audio.board_asr_frontend import BoardSpeechGate
    from board.runtime.audio.automatic_capture import SpeechEndpoint
    from board.runtime.audio.asr import SherpaOfflineRecognizer,AsrConfig
    models=Path('D:/AIModels/audio-frontend-eval-20261021')
    asr=PROJECT/'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14'
    source=asr/'test_wavs/0.wav'
    with wave.open(str(source),'rb') as wav:pcm=wav.readframes(wav.getnframes())
    config=s.OnlineSpeechDenoiserConfig(model=s.OfflineSpeechDenoiserModelConfig(
        gtcrn=s.OfflineSpeechDenoiserGtcrnModelConfig(model=str(models/'gtcrn_simple.onnx')),
        num_threads=1,provider='cpu'))
    original=s.OnlineSpeechDenoiser(config);candidate=FftGtcrnDenoiser(models/'gtcrn_simple.onnx',profile=True)
    old=[];new=[];segments=[];timings=dict(fft_ms=0.,ort_ms=0.,ifft_ola_ms=0.)
    for offset in range(0,len(pcm),640):
        samples=np.frombuffer(pcm[offset:offset+640],dtype='<i2').astype(np.float32)/32768
        start=time.perf_counter();expected=np.asarray(original(samples,16000).samples,dtype=np.float32);sdk_ms=(time.perf_counter()-start)*1000
        start=time.perf_counter();actual=candidate(samples).samples;fft_ms=(time.perf_counter()-start)*1000
        assert len(expected)==len(actual)
        segments.append(dict(samples=len(actual),max_abs_error=float(np.max(np.abs(expected-actual))) if len(actual) else 0.,sdk_ms=sdk_ms,fft_ms=fft_ms))
        for key in timings:timings[key]+=candidate.last_timing[key]
        old.append(expected);new.append(actual)
    tail1=np.asarray(original.flush().samples,dtype=np.float32);tail2=candidate.flush().samples
    assert len(tail1)==len(tail2)
    old.append(tail1);new.append(tail2)
    old=np.concatenate(old);new=np.concatenate(new)
    difference=old.astype(np.float64)-new.astype(np.float64)
    maximum=float(np.max(np.abs(difference)));rms=float(np.sqrt(np.mean(difference*difference)))
    assert len(old)==len(pcm)//2 and maximum<=1e-4 and rms<=1e-5
    sdk_gate=BoardSpeechGate(models);fft_gate=BoardFftSpeechGate(models)
    endpoint1=SpeechEndpoint(frame_classifier=sdk_gate,pre_roll_ms=500)
    endpoint2=SpeechEndpoint(frame_classifier=fft_gate,pre_roll_ms=500)
    emitted1=emitted2=None;vad1=[];vad2=[]
    # Two independent untouched-input endpoint owners; padding only closes the
    # public test utterance, with the current 700 ms silence rule unchanged.
    padded=pcm+b'\0'*48000
    for offset in range(0,len(padded),640):
        frame=padded[offset:offset+640].ljust(640,b'\0')
        if emitted1 is None:emitted1=endpoint1.feed(frame)
        if emitted2 is None:emitted2=endpoint2.feed(frame)
        if emitted1 is not None and emitted2 is not None:break
    assert emitted1 and emitted1==emitted2
    gate1=BoardSpeechGate(models);gate2=BoardFftSpeechGate(models)
    for offset in range(0,len(pcm),640):
        samples=np.frombuffer(pcm[offset:offset+640].ljust(640,b'\0'),dtype='<i2').astype(np.float32)/32768
        vad1.append(gate1(samples));vad2.append(gate2(samples))
    assert vad1==vad2
    decoder=SherpaOfflineRecognizer(AsrConfig(model_dir=str(asr),prefer_int8=True,num_threads=2))
    text1=decoder.transcribe(np.frombuffer(emitted1,dtype='<i2').astype(np.float32)/32768)
    text2=decoder.transcribe(np.frombuffer(emitted2,dtype='<i2').astype(np.float32)/32768)
    assert text1 and text1==text2
    # A stronger extra check: the denoised candidate PCM also transcribes the
    # same as SDK-denoised PCM, though production ASR still uses original PCM.
    clean_text1=decoder.transcribe(old)
    clean_text2=decoder.transcribe(new)
    assert clean_text1 and clean_text1==clean_text2
    result=dict(public_wav_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        sherpa_version=s.__version__,ort_version=candidate.ort_version,
        samples=len(old),segments=len(segments),max_abs_pcm_float_error=maximum,rms_pcm_float_error=rms,
        pcm16_equal_fraction=float(np.mean(np.rint(old*32768).clip(-32768,32767)==np.rint(new*32768).clip(-32768,32767))),
        flush_samples=len(tail1),same_vad_decisions=True,vad_frames=len(vad1),speech_frames=sum(vad1),
        vad_sha256=hashlib.sha256(bytes(vad1)).hexdigest(),same_endpoint_pcm=True,
        endpoint_samples=len(emitted1)//2,endpoint_sha256=hashlib.sha256(emitted1).hexdigest(),
        same_original_endpoint_asr=True,original_endpoint_asr=text1,
        same_denoised_asr=True,denoised_asr=clean_text1,
        sdk_mean_frame_ms=sum(v['sdk_ms'] for v in segments)/len(segments),
        fft_mean_frame_ms=sum(v['fft_ms'] for v in segments)/len(segments),segment_timings_ms=timings,
        actual_capture=False,actual_playback=False,production_changed=False)
    (HERE/'gtcrn_fft_windows_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
