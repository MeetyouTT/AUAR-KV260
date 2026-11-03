"""Prepare an isolated GUI with a visible finite edge-follow control."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/463c9307');G=R/'gui-release';N=R/'gui-face-edge-v4'
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v4')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not N.exists();m=json.loads((F/'deployment-manifest.json').read_text())
assert all(sha(x['destination'])==x['sha256'] for x in m['files'])
cfg=json.loads((G/'startup/config.json').read_text());old=Path(cfg['runtime'])
assert all(sha(old/'aura'/n)==v for n,v in cfg['component_sha256'].items())
N.mkdir(mode=0o700);shutil.copytree(old,N/'runtime',symlinks=True);(N/'startup').mkdir()
root=N/'runtime/aura';entry=root/'tools/board_avatar_pan.py'
text=entry.read_text();assert 'from tools.pan_controls import stage_type' in text and 'return ManualPanProcess(config)' in text
text=text.replace('from tools.pan_controls import stage_type','from tools.face_pan_controls import stage_type, FacePanProcess').replace('return ManualPanProcess(config)','return FacePanProcess(config)');entry.write_text(text)
helper=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v4/gui-src/face_pan_controls_e831dce5fef07f50.py');assert sha(helper)=='e831dce5fef07f5006dbe7cdeb2ee29525780bb11bf4128ec58e23ac1b70eab9'
shutil.copy2(helper,root/'tools/face_pan_controls.py')
s=json.loads((R/'state.json').read_text());board=Path(s['old_root']);ops=json.loads((F.parent/'meta.json').read_text())
follow={'release_root':str(F),'manifest_sha256':sha(F/'deployment-manifest.json'),'arguments':{
 'manifest':str(board/'candidate-manifest.json'),'manifest-sha256':sha(board/'candidate-manifest.json'),
 'context':str(R/'context.json'),'app-root':ops['candidate_root']+'/aura',
 'direction-evidence':str(R/'direction-calibration.json'),'human-evidence':str(G/'manual-release/human-observation.json')}}
(root/'config/pan_face.local.json').write_text(json.dumps(follow,indent=2)+'\n')
p=root/'config/pan_manual.local.json';manual=json.loads(p.read_text());manual['face_follow_config']=str(root/'config/pan_face.local.json');p.write_text(json.dumps(manual,indent=2)+'\n')
cfg['runtime']=str(N/'runtime');cfg['gui_sha256']=sha(entry)
for n in ('tools/board_avatar_pan.py','tools/face_pan_controls.py','config/pan_face.local.json','config/pan_manual.local.json'):cfg['component_sha256'][n]=sha(root/n)
shutil.copy2(G/'startup/launcher.py',N/'startup/launcher.py');(N/'startup/config.json').write_text(json.dumps(cfg,indent=2)+'\n')
env=dict(os.environ,DISPLAY=':0');p=subprocess.run(['/usr/bin/python3','-B',str(N/'startup/launcher.py'),'--config',str(N/'startup/config.json'),'--preflight'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=25)
assert p.returncode==0,p.stderr[-600:]
(N/'stage.json').write_text(json.dumps({'phase':'PREPARED','config_sha256':sha(N/'startup/config.json'),'launcher_sha256':sha(N/'startup/launcher.py')},indent=2)+'\n')
print(json.dumps({'phase':'PREPARED','components':len(cfg['component_sha256']),'gui':str(N),'physical_commands':0}))
