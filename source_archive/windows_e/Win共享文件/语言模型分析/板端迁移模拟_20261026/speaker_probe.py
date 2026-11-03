"""Read-only ECAPA model loading, CPU inference on four upstream public WAVs.

Skip from_hparams/collect_files to avoid copying or downloading checkpoints.
Only the embedding and normalization checkpoints are needed for encode_batch.
"""
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import probe
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

def main():
    import torch
    from hyperpyyaml import load_hyperpyyaml
    from speechbrain.inference.classifiers import EncoderClassifier
    from common.speaker_identity import EcapaEncoder, SpeakerStore, verify_model
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    directory = Path('D:/AIModels/speaker-identity/ecapa')
    started = time.perf_counter()
    model_id = verify_model(directory)
    with (directory/'hyperparams.yaml').open(encoding='utf-8') as handle:
        hparams = load_hyperpyyaml(handle, {'pretrained_path': str(directory)})
    pretrainer = hparams['pretrainer']
    pretrainer.loadables = {k: v for k, v in pretrainer.loadables.items()
                           if k in ('embedding_model', 'mean_var_norm_emb')}
    pretrainer.set_collect_in(directory)
    pretrainer.load_collected()
    encoder = EcapaEncoder.__new__(EcapaEncoder)
    encoder.model_id = model_id
    encoder.model = EncoderClassifier(modules=hparams['modules'], hparams=hparams, run_opts={'device': 'cpu'})
    encoder.model.mods.eval()
    load_ms = (time.perf_counter()-started)*1000
    root = Path('D:/AIModels/speaker-identity/public-samples')
    vectors, rows = {}, []
    for person in (1, 2):
        for sentence in (1, 2):
            name = 'spk%d_snt%d' % (person, sentence)
            path = root/(name+'.wav')
            raw = probe.load_wav(path)
            started = time.perf_counter()
            vectors[name] = encoder.encode(raw)
            rows.append({'public_sample': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'seconds': len(raw)/32000, 'encode_ms_windows': (time.perf_counter()-started)*1000,
                'dimension': len(vectors[name])})
    gallery = SpeakerStore(HERE/'public_speaker_smoke.sqlite3', model_id, 192, .6, .1, create=True)
    for person in (1, 2):
        gallery.enroll('public-%d' % person, 'Public sample %d' % person,
            vectors['spk%d_snt1' % person], consent=True, expected_revision=person-1)
    matches = []
    for person in (1, 2):
        match = gallery.match(vectors['spk%d_snt2' % person])
        matches.append({'query': 'spk%d_snt2' % person, 'state': match.state, 'score': match.score,
                        'expected_identity': 'public-%d' % person, 'identity': match.identity_id})
    gallery.close()
    scores = [{'reference': a, 'query': b, 'same_speaker': a[:4] == b[:4],
               'cosine': sum(x*y for x, y in zip(vectors[a], vectors[b]))}
              for a in ('spk1_snt1', 'spk2_snt1') for b in ('spk1_snt2', 'spk2_snt2')]
    assert all(m['state'] == 'KNOWN' and m['identity'] == m['expected_identity'] for m in matches)
    result = probe.metadata()
    result.update(status='WINDOWS_CPU_PUBLIC_SPEAKER_PASS', model_id=model_id, cpu_threads=1,
        load_ms=load_ms, rows=rows, scores=scores, matches=matches, process_memory=probe.memory(),
        field_calibrated=False, smoke_threshold=.6, smoke_margin=.1,
        real_personal_database_accessed=False, board_inference_proven=False,
        loader_scope='Read-only local checkpoint hooks; skipped unused classification/label checkpoints; original EcapaEncoder.encode reused')
    probe.write('speaker_model', result)

try:
    main()
except Exception as exc:
    probe.write('speaker_model_failure', {'status': 'FAILED', 'error_type': type(exc).__name__, 'error': str(exc), **probe.metadata()})
    raise
