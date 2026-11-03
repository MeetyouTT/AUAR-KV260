"""Root-only source staging/application for selected Yuki framing and palette."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

ROOT='/home/root/aura-character-xuefei-20261030/f94fca2c94288acb'
PATCH='/home/root/aura-character-appearance-20261030/waist-wine-v1'
NATIVE='/home/root/aura-character-xuefei-20261030/framing-264d34734302a36b/libaura_yuki.so'
NATIVE_SHA='887546c09eb1897845c8d7f55a9e3f9b9c761448c7410f2b599259ae0b51efd2'
SCRIPT=r'''
import base64,hashlib,json,os,sys
from pathlib import Path
TOOLS='/home/root/aura-character-xuefei-20261030/tools-c97bdb5e87268e2f'
sys.path.insert(0,TOOLS);import formal_publish as c
os.environ['PATH']='/usr/sbin:/usr/bin:/sbin:/bin'
p=c.parse(c.read(TOOLS+'/policy.json','b550e2a2307d97b52ba598a9e992f96ecacb53de05babf438d551a942de2996d'));p['_sha256']='b550e2a2307d97b52ba598a9e992f96ecacb53de05babf438d551a942de2996d'
root=Path(ROOT);patch=Path(PATCH);j=c.staged(p)
def replace(path,raw):
 tmp=path.with_name(path.name+'.appearance-new');c.create(tmp,raw);os.replace(str(tmp),str(path))
if ACTION=='prepare':
 assert j['phase']=='COMMITTED' and j['guard_removed'] and not patch.exists()
 assert c.sha(c.read(root/'startup/config.json'))=='91dbe7229cf0e11afdcfa6ca5aca657dd7f95a2adfa9b3764a0df0d793f050e2'
 assert j['manifest_sha256']=='bfdc28c79eff58e4ae6cc35df889f99232b4fdd64263dab5377a1b108c3fe7a0'
 c.state(p)
 plan=c.parse(c.read(root/'publish_manifest.json',j['manifest_sha256']));files={}
 for relative,(payload,pin) in INPUTS.items():
  raw=base64.b64decode(payload,validate=True);assert c.sha(raw)==pin
  assert relative in plan['files'];files[relative]=raw
 files['runtime/aura/tools/libaura_yuki.so']=c.read(NATIVE,NATIVE_SHA)
 meta=c.parse(c.read(root/'runtime/aura/config/yuki_pair.formal.json'))
 assert meta['runtime_pins']['tools/libaura_yuki.so']=='788ef5bb6b434ccf83c780059cb1dbb9246275fa8abc88e52d57a1d8c6042276'
 meta['runtime_pins']['tools/libaura_yuki.so']=NATIVE_SHA
 meta['presentation']=dict(revision='waist-wine-v1',camera=dict(top=-3500,bottom=-2090,center_x=-50,height_fill=.96),
     native_widget=dict(width=423,height=516),asset_profile_unchanged=True,extra_pixel_resampling=False)
 raw_meta=c.encoded(meta);files['runtime/aura/config/yuki_pair.formal.json']=raw_meta;meta_sha=c.sha(raw_meta)
 source=c.read(root/'runtime/aura/tools/formal_yuki.py').decode()
 before="PAIR_CONFIG_SHA256='9828c4665f9f2a15c20c09e8b5dc9646127acfca75bd593088a5a4e9f850056e'"
 assert source.count(before)==1;source=source.replace(before,"PAIR_CONFIG_SHA256='"+meta_sha+"'",1)
 files['runtime/aura/tools/formal_yuki.py']=source.encode()
 gui=c.parse(c.read(root/'runtime/aura/config/board_avatar_gtk.json'));gui['character_pair']['selection_sha256']=meta_sha
 files['runtime/aura/config/board_avatar_gtk.json']=c.encoded(gui)
 cfg=c.parse(c.read(root/'startup/config.json'))
 assert len(cfg['component_sha256'])==304
 for relative,raw in files.items():
  assert relative.startswith('runtime/aura/');cfg['component_sha256'][relative[len('runtime/aura/'):]]=c.sha(raw)
 files['startup/config.json']=c.encoded(cfg)
 for relative,raw in files.items():
  if relative.endswith('.py'):compile(raw,relative,'exec')
 changes={relative:dict(before_sha256=plan['files'][relative]['sha256'],after_sha256=c.sha(raw),bytes=len(raw)) for relative,raw in files.items()}
 patch.mkdir(mode=0o700)
 for relative,raw in files.items():
  out=patch/'staged'/relative;out.parent.mkdir(mode=0o700,parents=True,exist_ok=True);c.create(out,raw)
 spec=dict(phase='STAGED',base_startup_sha256='91dbe7229cf0e11afdcfa6ca5aca657dd7f95a2adfa9b3764a0df0d793f050e2',
     base_manifest_sha256=j['manifest_sha256'],changes=changes,presentation=meta['presentation'],
     palette='cream + uniform navy + ribbon wine',model_or_texture_changed=False,persona_changed=False,business_or_user_data_changed=False)
 c.create(patch/'spec.json',c.encoded(spec))
 print(json.dumps(dict(status='APPEARANCE_SOURCE_STAGED_NO_LIVE_CHANGE',patch=str(patch),changes=changes,presentation=meta['presentation'])))
elif ACTION=='apply':
 spec=c.parse(c.read(patch/'spec.json'));assert spec['phase']=='STAGED'
 c.inactive(p);j=c.staged(p);assert j['manifest_sha256']==spec['base_manifest_sha256']
 plan=c.parse(c.read(root/'publish_manifest.json',j['manifest_sha256']))
 backup=patch/'before';backup.mkdir(mode=0o700)
 c.create(backup/'publish_manifest.json',c.encoded(plan))
 for relative,row in spec['changes'].items():
  old=c.read(root/relative,row['before_sha256']);raw=c.read(patch/'staged'/relative,row['after_sha256'])
  out=backup/relative;out.parent.mkdir(mode=0o700,parents=True,exist_ok=True);c.create(out,old)
 # No UI owner is alive: replace files atomically, including the mapped-code library.
 for relative,row in spec['changes'].items():
  raw=c.read(patch/'staged'/relative,row['after_sha256']);replace(root/relative,raw)
  plan['files'][relative]=dict(bytes=len(raw),sha256=row['after_sha256'])
 plan['appearance_patch']=dict(patch=str(patch),presentation=spec['presentation'],base_manifest_sha256=spec['base_manifest_sha256'])
 encoded=c.encoded(plan);replace(root/'publish_manifest.json',encoded)
 j.update(phase='APPEARANCE_STARTING',manifest_sha256=c.sha(encoded),appearance_patch=plan['appearance_patch']);c.save(p,j)
 c.staged(p);c.command(c.new_command(p)+['--preflight'],timeout=20)
 c.command(['/bin/systemctl','--no-block','start',c.UNIT])
 spec.update(phase='APPLIED_START_REQUESTED',new_manifest_sha256=c.sha(encoded),new_startup_sha256=c.sha(c.read(root/'startup/config.json')))
 c.create(patch/'applied.json',c.encoded(spec))
 print(json.dumps(dict(status='APPEARANCE_APPLIED_NORMAL_START_REQUESTED',startup_sha256=spec['new_startup_sha256'],source_manifest_sha256=spec['new_manifest_sha256'],component_pins=304,model_or_texture_changed=False)))
else:raise ValueError('action')
'''

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('prepare','apply'));args=parser.parse_args()
    paths={'runtime/aura/tools/board_avatar_gtk.py':HERE/'root_overlay/aura/tools/board_avatar_gtk.py',
           'runtime/aura/ui/ui_tokens.json':HERE/'proposed_overlay/aura/ui/ui_tokens.json'}
    values=dict(ROOT=ROOT,PATCH=PATCH,NATIVE=NATIVE,NATIVE_SHA=NATIVE_SHA,ACTION=args.action,
        INPUTS={name:(base64.b64encode(path.read_bytes()).decode(),hashlib.sha256(path.read_bytes()).hexdigest()) for name,path in paths.items()})
    prefix='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'
    result=json.loads(ssh('python3 -B -',prefix+SCRIPT,timeout=55))
    out=HERE/('actual_'+args.action+'.json');out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(output=str(out),**result),ensure_ascii=True))

if __name__=='__main__':main()
