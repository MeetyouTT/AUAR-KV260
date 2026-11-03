"""Render actual GTK sampling counters with synthetic pixels; no visible window."""
import ast,base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
source=(HERE/'preflight.py').read_text(encoding='utf-8')
start=source.index('gui=r"""')+4;end=source.index('\nwidget=subprocess.run',start)
gui=ast.literal_eval(source[start:end])
gui=gui.replace("'target_kind':'face','face_target':key,'state':'UNKNOWN'", """'target_kind':'face','face_target':key,'state':'UNKNOWN','db_version':0,'people':[],
   'enrollment_sampling':{'session_id':'synthetic-session','stage':'left','counts':{'front':4,'left':1,'right':0,'validate':0},
   'total':5,'total_required':15,'detail':'请轻微向左转头，双眼保持可见'}""")
gui=gui.replace("'capabilities':{'identity_enroll':True}","'capabilities':{'identity_enroll':False,'identity_sample_start':False}")
gui=gui.replace('dialog=stage.create_identity_face_dialog();',"dialog=stage.create_identity_face_dialog(name='测试访客',target={'camera_epoch':'synthetic','track_id':7,'track_generation':1});")
gui=gui.replace("and panel['button'].get_sensitive()","and not panel['button'].get_sensitive()")
candidate=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
remote="""
import json,os,subprocess
from pathlib import Path
c=CANDIDATE
run=subprocess.run(['python3','-B','-c',GUI],cwd=Path(c['runtime'])/'aura',
 env=dict(os.environ,PYTHONPATH=str(Path(c['runtime'])/'aura'),PYTHONDONTWRITEBYTECODE='1',DISPLAY=':0'),
 capture_output=True,text=True,timeout=25)
if run.returncode:raise RuntimeError(run.stderr)
print(run.stdout)
""".replace('CANDIDATE',repr(candidate),1).replace('GUI',repr(gui),1)
result=json.loads(ssh('python3 -B -',remote,timeout=35))
(HERE/'sampling_progress_synthetic.png').write_bytes(base64.b64decode(result.pop('png_base64'),validate=True))
(HERE/'sampling_widget.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
