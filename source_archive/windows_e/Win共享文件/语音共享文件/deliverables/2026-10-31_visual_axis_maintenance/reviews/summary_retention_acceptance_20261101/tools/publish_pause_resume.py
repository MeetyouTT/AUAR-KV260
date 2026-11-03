"""Explicit serial publisher. Mutations require the requested internal local-review receipt."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time

HERE=Path(__file__).resolve().parents[1]
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh


def main():
    p=argparse.ArgumentParser();p.add_argument('direction',choices=('forward','rollback'))
    p.add_argument('action',choices=('inspect','guard','window-inspect','normal-close','apply','start','ready'))
    p.add_argument('--review',type=Path);p.add_argument('--window-proof',type=Path);a=p.parse_args()
    root=HERE/'package/pause_resume';mraw=(root/'BUNDLE_MANIFEST.json').read_bytes();manifest=json.loads(mraw)
    for name,expected in manifest['files'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
    if a.action!='inspect':
        assert a.review,'The main chat requested internal local review before applying this exact package.'
        review=json.loads(a.review.read_bytes())
        assert review['status']=='APPROVED_FOR_SERIAL_OPERATOR'
        assert review['bundle_manifest_sha256']==hashlib.sha256(mraw).hexdigest()
        assert review['candidate_source_sha256']=='54fa17ac97e3fdbeeb2725b6534a86dec9ece60839f2b14ffa77c348e714dafc'
    read=lambda name:json.loads((root/name).read_bytes())
    before=read('base_spec.json' if a.direction=='forward' else 'candidate_spec.json')
    after=read('candidate_spec.json' if a.direction=='forward' else 'base_spec.json')
    select_after=a.action in ('start','ready')
    spec=after if select_after else before
    startup=read(('candidate' if (a.direction=='forward')==select_after else 'base')+'_startup.json')
    token=window=None
    if a.action=='normal-close':
        assert a.window_proof
        proof=json.loads(a.window_proof.read_bytes())['result']
        assert proof['status']=='WINDOW_INSPECTED_NO_CLOSE';token=proof['review_token'];window=proof['window']['window_id']
    values=dict(ACTION=a.action,DIRECTION=a.direction,SPEC=spec,BASE_SPEC=before,NEW_SPEC=after,
                GUI=read('gui.json'),PLAN=read(a.direction+'_plan.json'),TOKEN=token,WINDOW=window,
                BINDING_SOURCE=(root/'camera_binding_runtime.py').read_text('utf-8'))
    source='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'
    source+=(root/'publisher_definitions.py').read_text('utf-8')+'\n'
    source+=(root/'single_projection_overlay.py').read_text('utf-8')+'\n'
    source+="import types\nBINDING=types.ModuleType('_current_camera_binding')\nexec(compile(BINDING_SOURCE,'<pinned-camera-binding>','exec'),BINDING.__dict__)\n"
    source+='EXPECTED_GUI=GUI\nEXPECTED_STARTUP='+repr(startup)+'\n'
    source+="print(json.dumps(dispatch_single_projection(),allow_nan=False))\n"
    value=json.loads(ssh('python3 -B -',source,timeout=230 if a.action=='ready' else 120))
    target=HERE/'evidence'/('pause_resume_'+a.direction+'_'+a.action.replace('-','_')+'_'+str(time.time_ns())+'.json')
    envelope=dict(direction=a.direction,action=a.action,source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                  bundle_manifest_sha256=hashlib.sha256(mraw).hexdigest(),result=value)
    raw=(json.dumps(envelope,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    with target.open('xb') as f:f.write(raw)
    print(json.dumps(dict(evidence=str(target),result=value),ensure_ascii=False))


if __name__=='__main__':main()
