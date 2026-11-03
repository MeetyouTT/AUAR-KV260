"""Read-only black-screen diagnosis after user-declared live failure."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
remote=r'''
import json,subprocess,urllib.request
from pathlib import Path
out={}
for label,port,path in [('ui',8783,'/api/state'),('camera',8790,'/health')]:
 try:out[label]=json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3))
 except Exception as e:out[label]={'error':str(e)}
for name,args in [('services',['systemctl','show','aura-avatar-ui.service','-p','ActiveState','-p','SubState','-p','MainPID','-p','NRestarts']),
 ('memory',['free','-m']),('journal',['journalctl','-u','aura-avatar-ui.service','-n','25','--no-pager']),
 ('oom',['dmesg','--ctime']),('xwindows',['xwininfo','-root','-tree'])]:
 try:
  r=subprocess.run(args,capture_output=True,text=True,timeout=8,env=dict(__import__('os').environ,DISPLAY=':0'))
  out[name]=r.stdout[-14000:]+r.stderr[-2000:]
 except (OSError,subprocess.TimeoutExpired) as e:out[name]=str(e)
out['oom']='\n'.join(row for row in out['oom'].splitlines() if any(x in row.lower() for x in ('killed process','out of memory','oom-kill','segfault')))
p=Path(RUNTIME)/'managed-runs'
out['logs']={str(f):f.read_text()[-10000:] for f in sorted(p.glob('*/stage.log'))[-2:]}
print(json.dumps(out))
'''.replace('RUNTIME',repr(c['runtime']),1)
r=json.loads(ssh('python3 -B -',remote,timeout=40))
(HERE/'black_screen_diagnosis.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
u=r.pop('ui');print(json.dumps(r));print(json.dumps({k:u.get(k) for k in ('error','phase','handsfree_dialogue','avatar_renderer','audio_output_state')}))
