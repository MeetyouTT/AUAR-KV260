"""Explicit serial execution of the frozen original-configuration restoration."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE.parents[3]/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('guard','window-inspect','normal-close','apply','start','ready'))
    p.add_argument('--bundle',choices=('original_restore','original_direction_fix'),default='original_restore')
    p.add_argument('--window-proof',type=Path);a=p.parse_args()
    root=HERE/'package'/a.bundle;manifest=json.loads((root/'publisher_bundle_manifest.json').read_bytes())
    for name,expected in manifest['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected
    read=lambda name:json.loads((root/name).read_bytes())
    base=read('base_spec.json');new=read('new_spec.json');binding=read('binding.json')
    spec=dict(base,camera_owner=binding['camera_owner'],face_readback=binding['face_readback']) if a.action in ('guard','window-inspect','normal-close','apply') else new
    token=window=None
    if a.action=='normal-close':
        assert a.window_proof
        proof=json.loads(a.window_proof.read_bytes())['result']
        assert proof['status']=='WINDOW_INSPECTED_NO_CLOSE';token=proof['review_token'];window=proof['window']['window_id']
    values=dict(ACTION=a.action,SPEC=spec,BASE_SPEC=base,NEW_SPEC=new,OLD_GUI=read('old_gui.json'),NEW_GUI=read('new_gui.json'),
        PLAN=read('plan.json'),TOKEN=token,WINDOW=window,BINDING_SOURCE=(root/'camera_binding_runtime.py').read_text(encoding='utf-8'))
    prefix='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'
    definitions=(root/'publisher_definitions.py').read_text(encoding='utf-8')
    overlay=(root/manifest.get('overlay_relative','../../tools/original_publisher_overlay.py')).read_text(encoding='utf-8')
    setup="\nBINDING=types.ModuleType('_current_camera_binding');exec(compile(BINDING_SOURCE,'<pinned-current-camera-binding>','exec'),BINDING.__dict__)\n"
    # Definitions load the original exact expected configuration. After loading,
    # select its reviewed new configuration only for the new normal start/ready.
    select="\nif ACTION in ('start','ready'):\n EXPECTED_GUI=NEW_GUI;EXPECTED_STARTUP="+repr(read('new_startup.json'))+"\n"
    source=prefix+definitions+'\n'+overlay+setup+select+"\nprint(json.dumps(dispatch_original(),allow_nan=False))\n"
    raw=ssh('python3 -B -',source,timeout=230 if a.action=='ready' else 120)
    result=json.loads(raw)
    output=HERE/'evidence'/('original_publish_'+a.action.replace('-','_')+'_'+str(time.time_ns())+'.json')
    data=dict(action=a.action,remote_sha256=hashlib.sha256(source.encode()).hexdigest(),result=result)
    output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(evidence=str(output),result=result),ensure_ascii=False))

if __name__=='__main__':main()
