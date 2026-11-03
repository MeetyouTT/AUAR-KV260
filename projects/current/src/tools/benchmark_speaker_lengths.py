"""Compute-only duration benchmark on repeated public audio, not accuracy."""
import argparse
import json
from pathlib import Path
import socket
import statistics
import sys
import time
import wave

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common.speaker_identity import EcapaEncoder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-directory',type=Path,required=True)
    parser.add_argument('--sample',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    def blocked(*args,**kwargs): raise RuntimeError('Network blocked')
    socket.socket.connect = blocked
    import torch
    torch.set_num_threads(2)
    encoder = EcapaEncoder(args.model_directory)
    with wave.open(str(args.sample)) as audio:
        if (audio.getframerate(),audio.getnchannels(),audio.getsampwidth()) != (16000,1,2):
            raise ValueError('Require PCM16 mono 16kHz public sample')
        source = audio.readframes(audio.getnframes())
    results = {}
    encoder.encode(source)
    for seconds in (6,10,20):
        pcm = (source*(seconds*32000//len(source)+1))[:seconds*32000]
        timings = []
        for repeat in range(3):
            started=time.perf_counter();encoder.encode(pcm)
            timings.append(round((time.perf_counter()-started)*1000,2))
        results[str(seconds)] = {'elapsed_ms':timings,'median_ms':statistics.median(timings)}
    result = {'scope':'COMPUTE_ONLY_REPEATED_PUBLIC_AUDIO_NOT_ACCURACY',
              'cpu_threads':2,'model_id':encoder.model_id,'durations_seconds':results}
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__ == '__main__': main()
