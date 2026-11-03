"""Public same-WAV decision comparison: accepted host pipeline vs board adapter."""
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
import wave

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
sys.path.insert(0,str(PROJECT/'aura'))


def main():
    import numpy as np
    import sherpa_onnx
    from tools.audio_frontend_host import Pipeline
    from board.runtime.audio.board_asr_frontend import BoardSpeechGate
    root=Path('D:/AIModels/audio-frontend-eval-20261021')
    source=PROJECT/'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/0.wav'
    with wave.open(str(source),'rb') as wav:
        assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(1,2,16000)
        pcm=wav.readframes(wav.getnframes())
    original=Pipeline(root)
    start=time.perf_counter();candidate=BoardSpeechGate(root);load=time.perf_counter()-start
    decisions=[];durations=[]
    for offset in range(0,len(pcm),640):
        frame=pcm[offset:offset+640].ljust(640,b'\0')
        before=frame
        expected,_=original.process(frame)
        start=time.perf_counter()
        actual=candidate(np.frombuffer(frame,dtype='<i2').astype(np.float32)/32768)
        durations.append((time.perf_counter()-start)*1000)
        assert expected==actual and frame==before
        decisions.append(actual)
    result=dict(platform='Windows',public_wav_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        sherpa_onnx=sherpa_onnx.__version__,numpy=np.__version__,same_decisions_as_current_host=True,
        frames=len(decisions),speech_frames=sum(decisions),decision_sha256=hashlib.sha256(bytes(decisions)).hexdigest(),
        load_seconds=round(load,4),mean_frame_ms=round(statistics.mean(durations),4),
        max_frame_ms=round(max(durations),4),processed_samples=candidate.samples,
        unchanged_pcm=True,actual_capture=False,actual_playback=False)
    (HERE/'frontend_windows_public_result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
