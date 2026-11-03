"""Public samples smoke test, explicitly not field calibration or enrollment."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import statistics
import sys
import time
import wave

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common.speaker_identity import EcapaEncoder, SpeakerStore, read_pcm, voiced_pcm


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-directory',required=True,type=Path)
    parser.add_argument('--samples',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--scratch-database',required=True,type=Path)
    args = parser.parse_args()
    # Any attempted network access during model load/inference must fail.
    def blocked(*args,**kwargs): raise RuntimeError('Network forbidden during offline verification')
    socket.socket.connect = blocked
    import torch
    torch.set_num_threads(2)
    started = time.perf_counter()
    encoder = EcapaEncoder(args.model_directory)
    load_ms = (time.perf_counter()-started)*1000
    vectors = {}; timings = {}; hashes = {}; gates = {}
    for name in ('spk1_snt1.wav','spk1_snt2.wav','spk2_snt1.wav','spk2_snt2.wav'):
        path = args.samples/name
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            _, quality = voiced_pcm(read_pcm(path))
            gates[name] = {'state':'ACCEPTED',**quality}
        except ValueError as exc:
            gates[name] = {'state':'REJECTED','reason':str(exc)}
        with wave.open(str(path)) as audio:
            if (audio.getframerate(),audio.getnchannels(),audio.getsampwidth()) != (16000,1,2):
                raise ValueError('Unexpected public sample format')
            raw = audio.readframes(audio.getnframes())
        timings[name] = []
        for repeat in range(3):
            started = time.perf_counter(); vector = encoder.encode(raw)
            timings[name].append(round((time.perf_counter()-started)*1000,2))
        vectors[name] = vector
    scores = []
    names = list(vectors)
    for i,name in enumerate(names):
        for other in names[i+1:]:
            score = sum(a*b for a,b in zip(vectors[name],vectors[other]))
            scores.append({'first':name,'second':other,'same_speaker':name[:4]==other[:4],'cosine':score})
    positive = [r['cosine'] for r in scores if r['same_speaker']]
    negative = [r['cosine'] for r in scores if not r['same_speaker']]
    separation = min(positive) > max(negative)
    gallery_check = {'passed':False}
    if separation:
        # Demonstrates decision mechanics with one public reference, not 3-recording enrollment acceptance.
        temporary_threshold = (min(positive)+max(negative))/2
        if args.scratch_database.exists(): raise ValueError('Use a fresh scratch database')
        store = SpeakerStore(args.scratch_database,encoder.model_id,192,temporary_threshold,.1,create=True)
        try:
            store.enroll('public-spk1','Public speaker 1',vectors['spk1_snt1.wav'],consent=True,expected_revision=0)
            same = store.match(vectors['spk1_snt2.wav'])
            stranger = store.match(vectors['spk2_snt1.wav'])
            gallery_check = {'passed':same.state=='KNOWN' and stranger.state=='UNKNOWN',
                             'same_state':same.state,'stranger_state':stranger.state,
                             'smoke_only_threshold':temporary_threshold}
        finally: store.close()
    result = {'status':'PASS_PUBLIC_SMOKE' if separation and gallery_check['passed'] else 'FAIL_PUBLIC_SMOKE',
              'field_calibrated':False,'production_deployed':False,'network_blocked':True,
              'model_id':encoder.model_id,'torch':torch.__version__,'cpu_threads':2,'dimension':192,
              'load_ms':round(load_ms,2),'inference_ms':timings,
              'warm_median_ms':statistics.median([x for rows in timings.values() for x in rows[1:]]),
              'pairs':scores,'gallery_smoke':gallery_check,'sample_sha256':hashes,'production_audio_gate':gates,
              'limitations':['Only 2 public speakers; short English samples bypass production duration/VAD gate.',
                             'No actual microphone, Chinese speech, multi-recording enrollment or cross-session accuracy acceptance.']}
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    if result['status'] != 'PASS_PUBLIC_SMOKE': raise SystemExit(1)


if __name__ == '__main__': main()
