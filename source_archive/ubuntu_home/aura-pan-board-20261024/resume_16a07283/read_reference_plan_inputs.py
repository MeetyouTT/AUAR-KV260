import hashlib,json,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
cfg=json.loads((G/'startup/config.json').read_text())
assert all(hashlib.sha256((A/n).read_bytes()).hexdigest()==h for n,h in cfg['component_sha256'].items())
names=('board/motion/manual_vsrv.py','board/motion/manual_process.py','board/motion/manual_live_config.py','board/motion/follow_readback.py')
files={n:dict(sha256=hashlib.sha256((A/n).read_bytes()).hexdigest(),source=(A/n).read_text()) for n in names}
manual=json.loads((A/'config/pan_manual.local.json').read_text());face=json.loads((A/'config/pan_face.local.json').read_text())
state=json.loads((R/'state.json').read_text());old=Path(state['old_root'])
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:m=json.load(f)['manual_pan']
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0
print(json.dumps({'manual_config':manual,'face_config':face,'manual':m,'files':files,
 'old_root':str(old),'old_manifest':json.loads((old/'candidate-manifest.json').read_text()),
 'bench':(old/'bench_finite_step.py').read_text(),'context':json.loads((R/'context.json').read_text()),'motor_commands_sent':0}))
