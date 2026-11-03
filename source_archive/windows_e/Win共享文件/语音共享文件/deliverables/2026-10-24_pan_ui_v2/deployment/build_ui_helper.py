import base64,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
baseline=json.loads((ROOT/'deploy-context.json').read_text())
gui=json.loads((ROOT/'gui-baseline.json').read_text())
assert baseline['boot']==gui['boot'] and baseline['native_critical'] and not baseline['owner_fenced']
names=['board/motion/manual.py','board/motion/manual_vsrv.py','board/motion/manual_process.py',
       'board/motion/vsrv_driver.py','board/motion/vsrv_transport.py','board/motion/input_freshness.py',
       'board/motion/manual_release.py','tools/pan_controls.py']
files={}
for name in names:
 raw=(ROOT/'runtime/aura'/name).read_bytes();files['runtime/aura/'+name]={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
for source,name in [('observed-trial.json','manual-release/observed-trial.json'),('human_observation.json','manual-release/human-observation.json')]:
 raw=(ROOT/source).read_bytes();files[name]={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
board=Path('/home/ghmd/aura-pan-joint-20261023/bundle/candidate-manifest.json')
tag=hashlib.sha256(json.dumps({n:x['sha256'] for n,x in files.items()},sort_keys=True).encode()).hexdigest()[:16]
meta={'root':'/home/root/aura-pan-ui-v2-20261024/observed-'+tag,'tag':tag,'baseline':baseline,
      'baseline_python_sha256':gui['gui_python_manifest'],'board_candidate_manifest_sha256':hashlib.sha256(board.read_bytes()).hexdigest()}
raw=json.dumps({'meta':meta,'files':files},separators=(',',':')).encode();payload=base64.b64encode(gzip.compress(raw,mtime=0)).decode()
helper=ROOT/'prepare_ui_helper.py';helper.write_text('PAYLOAD='+repr(payload)+'\nPAYLOAD_SHA='+repr(hashlib.sha256(raw).hexdigest())+'\n'+(ROOT/'prepare_ui_body.py').read_text())
(ROOT/'ui-release-plan.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps({'helper':str(helper),'source_bytes':helper.stat().st_size,'root':meta['root'],'patches':len(names),'no_board_action_yet':True}))
