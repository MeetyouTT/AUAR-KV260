import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
seconds=int(sys.argv[1]) if len(sys.argv)>1 else 60
remote=r'''
import time,json,urllib.request,subprocess
rows=[];start=time.monotonic()
while time.monotonic()-start<SECONDS:
 try:
  s=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
  rows.append({'at':time.monotonic(),'phase':s.get('phase'),'state':s.get('state'),'error':s.get('error'),'display':s.get('avatar_display'),'renderer':s.get('avatar_renderer'),'audio':s.get('audio_output_state'),'handsfree':s.get('handsfree_dialogue')})
 except Exception as exc:rows.append({'at':time.monotonic(),'error':str(exc)})
 time.sleep(2)
print(json.dumps({'rows':rows,'processes':subprocess.getoutput("ps -eo pid,pcpu,rss,args --sort=-pcpu | head -9")}))
'''.replace('SECONDS',str(seconds))
r=json.loads(ssh('python3 -B -',remote,timeout=seconds+20));(HERE/('monitor_%ds.json'%seconds)).write_text(json.dumps(r,indent=2),encoding='utf-8')
rows=[v for v in r['rows'] if v.get('display')];print(json.dumps({'samples':len(rows),'first':rows[0] if rows else None,'last':rows[-1] if rows else None,'processes':r['processes']}))
