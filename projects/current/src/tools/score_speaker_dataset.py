"""Extract scores from an explicit labelled, session-separated WAV dataset."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common.speaker_identity import EcapaEncoder, enrollment_vector, read_pcm, voiced_pcm
from common.speaker_validation import validate_trial_partitions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--model-directory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--consistency',type=float,required=True)
    parser.add_argument('--cpu-threads',type=int,default=2)
    args = parser.parse_args()
    if not 1 <= args.cpu_threads <= 4: parser.error('Use 1–4 CPU threads')
    data = json.loads(args.manifest.read_text(encoding='utf-8'))
    prepared = []; digests = set(); session_roles = {}
    for row in data['recordings']:
        if row['role'] not in ('enrollment','calibration','held_out') or not row['identity_id'] or not row['session_id']:
            raise ValueError('Invalid role or missing identity/session')
        session = row['session_id']
        if session in session_roles and session_roles[session] != row['role']:
            raise ValueError('Recording session reused across splits')
        session_roles[session] = row['role']
        raw = read_pcm(args.manifest.parent/row['wav'])
        digest = hashlib.sha256(raw).hexdigest()
        if digest in digests: raise ValueError('Duplicate PCM across dataset')
        digests.add(digest)
        trimmed,quality = voiced_pcm(raw)
        prepared.append((dict(row,pcm_sha256=digest,quality=quality),trimmed))
    if set(session_roles.values()) != {'enrollment','calibration','held_out'}:
        raise ValueError('Need enrollment, calibration and held-out recordings')
    import torch
    torch.set_num_threads(args.cpu_threads)
    encoder = EcapaEncoder(args.model_directory)
    embeddings = []
    for row,pcm in prepared:
        started = time.perf_counter(); vector = encoder.encode(pcm)
        embeddings.append((dict(row,inference_ms=round((time.perf_counter()-started)*1000,2)),vector))
    groups = {}
    for row,vector in embeddings:
        if row['role'] == 'enrollment': groups.setdefault(row['identity_id'],[]).append(vector)
    if not groups: raise ValueError('Empty enrolled gallery')
    gallery = {key:enrollment_vector(vectors,192,args.consistency) for key,vectors in groups.items()}
    result = {'model_id':encoder.model_id,'enrollment_pcm_sha256':[], 'enrollment_session_ids':[],
              'calibration':[], 'held_out':[], 'thresholds':data['thresholds'],'margins':data['margins'],
              'field_calibrated':False}
    for row,vector in embeddings:
        if row['role'] == 'enrollment':
            result['enrollment_pcm_sha256'].append(row['pcm_sha256'])
            result['enrollment_session_ids'].append(row['session_id'])
        else:
            # Never serialize embeddings or copy source audio to the report.
            result[row['role']].append({key:row[key] for key in
                ('identity_id','session_id','pcm_sha256','quality','inference_ms')})
            result[row['role']][-1]['scores'] = {
                key:sum(a*b for a,b in zip(vector,template)) for key,template in gallery.items()}
    validate_trial_partitions(result['calibration'],result['held_out'])
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'state':'SCORED_NOT_CALIBRATED','model_id':encoder.model_id,
                      'calibration_trials':len(result['calibration']),
                      'held_out_trials':len(result['held_out'])}))


if __name__ == '__main__': main()
