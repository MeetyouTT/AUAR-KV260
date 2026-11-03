import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
remote=r'''
import base64,json,subprocess,sys,time
from pathlib import Path
c=CANDIDATE;sys.path.insert(0,c['runtime']+'/aura')
import cv2
cv2.setNumThreads(2)
from board.identity.camera_faces import CameraFaceExtractor,config_for
e=CameraFaceExtractor(config_for(Path(c['runtime'])/'aura','config/board_identity.json'))
image=cv2.imread('/home/root/aura-adaptation-20261006/identity/reference/lena.jpg');h,w=image.shape[:2]
obs={'tracks':[{'track_id':1,'generation':1,'visible':True,'confirmed':True,'box':[0,0,w,h]}]}
rows=[]
for i in range(3):
 started=time.monotonic()
 try:
  vector,reason=e.extract(image,obs,{'track_id':1,'track_generation':1})
  rows.append({'ms':round((time.monotonic()-started)*1000,2),'valid':vector is not None,'reason':reason})
 except Exception as ex:rows.append({'exception':str(ex)})
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
import re
cfg=json.loads(Path(re.search(r'--config (\S+)',unit).group(1)).read_text());ui=Path(cfg['runtime'])/'aura'
sources={n:base64.b64encode((ui/n).read_bytes()).decode() for n in ['board/interaction/ui_contract.py','board/interaction/ui_services.py']}
print(json.dumps({'static_extractions':rows,'ui_sources':sources}))
'''.replace('CANDIDATE',repr(c))
r=json.loads(ssh('python3 -',remote,timeout=45))
import base64,difflib
diffs={}
for name,raw in r.pop('ui_sources').items():
 content=base64.b64decode(raw,validate=True);path=HERE/'before_ui'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
 diffs[name]=''.join(difflib.unified_diff(content.decode().splitlines(True),(ROOT/'aura'/name).read_text(encoding='utf-8').splitlines(True),fromfile='active',tofile='local'))
(HERE/'ui_diff.txt').write_text('\n'.join(diffs.values()),encoding='utf-8')
(HERE/'reference_diagnostic.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=True));print('\n'.join(diffs.values())[:7000])
