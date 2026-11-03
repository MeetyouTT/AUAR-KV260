"""Audit E2 raw delivery, reproduce proxy metrics, export fixed-coordinate visual evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent
BATCH = OUT.parent
E1 = BATCH.parent / 'batch_002_probe'
RAW = BATCH / 'raw/e2_rest_s421001_L124_guide62'
BASE = E1 / 'raw/e1_rest_s421001_L124'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(name, data):
    (OUT/name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    meta = read(RAW/'meta.json')
    manifest = read(BATCH/'workflows/e2_rest_s421001_L124_guide62_manifest.json')
    g1 = E1/'workflows/e1_rest_s421001_L124_api.json'
    g2 = BATCH/'workflows/e2_rest_s421001_L124_guide62_api.json'
    assert sha(g1) == manifest['source_graph_sha256']
    assert sha(g2) == manifest['probe_graph_sha256'] == meta['api_graph_sha256']
    before, after = read(g1), read(g2)
    restored = copy.deepcopy(after)
    added = restored.pop('15')
    assert added == {'class_type': 'MiniMaxH3AddGuide', 'inputs': {
        'positive': ['7',0], 'latent': ['7',1], 'frame_idx':62, 'vae':['3',0], 'image':['5',0]}}
    assert restored['10']['inputs']['conditioning'] == ['15',0]
    restored['10']['inputs']['conditioning'] = ['7',0]
    assert restored == before
    records=[]
    files=sorted(RAW.glob('*.png'))
    assert [p.name for p in files] == [f'{i:06d}.png' for i in range(124)]
    for p in files:
        with Image.open(p) as im:
            im.load()
            assert im.size == (864,1536)
            records.append({'file':p.name, 'mode':im.mode, 'size':list(im.size), 'sha256':sha(p)})
    assert records[0]['sha256'] == meta['sha256_first']
    assert records[-1]['sha256'] == meta['sha256_last']
    integrity={'frame_count':124,'all_readable_and_consecutive':True,
        'meta_hashes_match':True,'graph_change_verified':'Only guide node 15 at frame 62 and conditioning rewire',
        'source_graph_sha256':sha(g1),'graph_sha256':sha(g2),'frames':records}
    # Ensure comparison E1 is the same raw data inspected in the previous reception audit.
    old_records=read(E1/'review_20261006/integrity.json')['frames']
    assert all(sha(BASE/r['file']) == r['sha256'] for r in old_records)
    integrity['e1_all_124_hashes_match_previous_audit']=True
    save('integrity.json',integrity)
    helper=load('previous_audit',E1/'review_20261006/audit_received.py')
    helper.OUT=OUT
    metric=load('proxy_metrics',E1/'tools/drift_metrics_v2.py')
    cases=[]
    for label, folder in [('E1',BASE),('E2',RAW)]:
        rows=[metric.metrics(p) for p in sorted(folder.glob('*.png'))]
        assert len(rows)==124 and all(r is not None for r in rows)
        vectors={k:np.asarray([r[k]-rows[0][k] for r in rows],dtype=float) for k in metric.KEYS}
        vectors['hand_skin_shift']=np.hypot(vectors['hand_skin_x'],vectors['hand_skin_y'])
        assert all(np.isfinite(v).all() for v in vectors.values())
        summary={}
        for name,(start,stop) in {'all':(0,124),'before_62':(0,62),'from_62':(62,124)}.items():
            summary[name]={}
            for key,values in vectors.items():
                peak=start+int(np.abs(values[start:stop]).argmax())
                summary[name][key]={'max_source_px':round(float(abs(values[peak])),4),'frame':peak}
        cases.append({'case':label,'summary':summary,'per_frame':rows})
        hand_peak=summary['all']['hand_skin_shift']['frame']
        helper.sheet(folder,[0,hand_peak,62,123],f'{label}_hands.png',[(270,470,585,780)],width=315)
    save('proxy_metrics.json',{'caution':'All spans include hair. Skin centroid is an appearance proxy, not wrist tracking. Segment deviations use each clip first frame, not segment first frame. Not an acceptance gate.','cases':cases})
    for start in (0,64):
        helper.sheet(RAW,list(range(start,min(start+64,124))),f'faces_{start:03d}.png',[(310,170,540,340)],width=184,columns=8)
    helper.sheet(RAW,[0,17,19,26,46,62,85,123],'E2_keyframes.png',[(0,0,864,1536),(285,95,570,345),(260,345,590,790)],width=190)
    helper.sheet(RAW,[42,44,45,46,47,49,51,81,82,83,84,85,87,90],'E2_blink_evidence.png',[(310,170,540,340)],width=184,columns=7)
    # Same timepoints, same unregistered crops for before-anchor comparison.
    for label,folder in [('E1',BASE),('E2',RAW)]:
        helper.sheet(folder,[0,17,19,26,62,85,123],f'{label}_pose_comparison.png',[(260,345,590,790)],width=220)
    print(json.dumps({'integrity':{k:v for k,v in integrity.items() if k!='frames'},
        'metrics':[{k:v for k,v in c.items() if k!='per_frame'} for c in cases]},indent=2))


if __name__=='__main__':
    main()
