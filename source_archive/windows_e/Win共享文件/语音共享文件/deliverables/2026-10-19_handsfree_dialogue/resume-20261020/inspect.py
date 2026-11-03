"""Read current services and microphone holders; never opens a capture device."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import glob,json,subprocess,urllib.request
from pathlib import Path
out={}
for name,port,path in [('ui',8783,'/api/state'),('camera',8790,'/health'),('vision',8790,'/v1/ui/status')]:
 try:out[name]=json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
 except Exception as e:out[name]={'error':str(e)}
for name in ('aura-avatar-ui.service','aura-camera-ui.service'):
 out[name]=subprocess.check_output(['systemctl','cat',name],text=True)
out['capture_holders']=subprocess.run(['fuser',*glob.glob('/dev/snd/pcm*c')],capture_output=True,text=True).stdout
out['audio_processes']=[p for p in subprocess.check_output(['ps','-eo','pid,args'],text=True).splitlines() if any(x in p for x in ('speaker_sampler.py','gst-launch','arecord'))]
rows=subprocess.check_output(['ps','-eo','pid,args'],text=True).splitlines()
pids=[int(row.split()[0]) for row in rows if '/aura/tools/board_avatar_gtk.py' in row]
home=Path.home()
if len(pids)==1:
 env=dict(v.split('=',1) for v in Path('/proc/%d/environ'%pids[0]).read_bytes().decode().split('\0') if '=' in v)
 home=Path(env.get('HOME',str(home)))
p=home/'.local/share/aura/handsfree_dialogue.json';out['preference_path']=str(p)
out['preference']=p.read_text() if p.exists() else None
print(json.dumps(out))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=30))
(HERE/'before_state.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
u=r.get('ui',{})
print(json.dumps({k:v for k,v in r.items() if k not in ('ui','vision')},ensure_ascii=True))
print(json.dumps({k:u.get(k) for k in ('phase','playing','handsfree_dialogue','local_recording','automatic_conversation','audio_output_state','local_transcription')},ensure_ascii=True))
