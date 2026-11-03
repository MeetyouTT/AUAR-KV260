"""Explicit offline WAV enrollment/query; no production service changes."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.speaker_identity import SpeakerStore
from common.speaker_identity import EcapaEncoder, enrollment_vector, read_pcm, voiced_pcm


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['enroll', 'query'])
    parser.add_argument('--model-directory', required=True, type=Path)
    parser.add_argument('--model-id', help='Optional expected file fingerprint; otherwise derived from manifest')
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--threshold', required=True, type=float)
    parser.add_argument('--margin', required=True, type=float)
    parser.add_argument('--consistency', type=float)
    parser.add_argument('--person-id')
    parser.add_argument('--name')
    parser.add_argument('--consent', action='store_true')
    parser.add_argument('--expected-revision', type=int)
    parser.add_argument('--cpu-threads', type=int, default=2)
    parser.add_argument('wav', nargs='+', type=Path)
    args = parser.parse_args()
    if not 1 <= args.cpu_threads <= 4:
        parser.error('Use 1–4 CPU threads in this isolated prototype')
    if args.database.name == 'identities.sqlite3':
        parser.error('Use a separate speaker prototype database, not the face database')
    if args.action == 'enroll' and (not args.consent or not args.person_id or not args.name
                                     or args.consistency is None or args.expected_revision is None):
        parser.error('Enrollment requires consent, person ID, name, consistency and expected revision')
    if args.action == 'query' and len(args.wav) != 1:
        parser.error('Query takes one recording')
    recordings = [read_pcm(path) for path in args.wav]
    if args.action == 'enroll' and len({hashlib.sha256(r).digest() for r in recordings}) != len(recordings):
        parser.error('Duplicate enrollment audio')
    import torch
    torch.set_num_threads(args.cpu_threads)
    encoder = EcapaEncoder(args.model_directory, args.model_id)
    prepared = [voiced_pcm(raw) for raw in recordings]
    vectors = [encoder.encode(raw) for raw,quality in prepared]
    store = SpeakerStore(args.database, encoder.model_id, encoder.dimension, args.threshold, args.margin,
                         create=args.action == 'enroll')
    try:
        if args.action == 'enroll':
            vector = enrollment_vector(vectors, encoder.dimension, args.consistency)
            other = store.best_other_score(vector, exclude_id=args.person_id)
            if other is not None and other >= args.threshold:
                raise ValueError('Voice overlaps another enrolled identity; do not commit')
            store.enroll(args.person_id, args.name, vector, consent=True, expected_revision=args.expected_revision)
            result = {'state': 'ENROLLED', 'revision': store.revision}
        else:
            result = asdict(store.match(vectors[0]))
        print(json.dumps({'prototype': True, 'field_calibrated': False, 'model_id': encoder.model_id,
                          'quality': [quality for raw,quality in prepared], 'result': result}, ensure_ascii=False))
    finally:
        store.close()


if __name__ == '__main__':
    main()
