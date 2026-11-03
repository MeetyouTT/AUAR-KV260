"""Stream the bounded read-only monitor through the original strict SSH transport."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
here=Path(__file__).resolve().parent
source_path=here/'live_monitor_1.py';source=source_path.read_bytes();compile(source,str(source_path),'exec')
helper=here.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('verified_board_transport',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
intent=here/'LIVE_TRIAL_1_HOST_INTENT.json';output=here/'LIVE_TRIAL_1.jsonl';result=here/'LIVE_TRIAL_1_RESULT.json';assert not any(p.exists() for p in (intent,output,result))
with intent.open('x',encoding='utf-8') as f:json.dump({'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'script_sha256':hashlib.sha256(source).hexdigest(),'single_readonly_submission':True},f)
args=[m.SSH,'-i',str(m.KEY),'-o','UserKnownHostsFile='+str(m.KNOWN_HOSTS),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=4','root@192.168.50.2','python3 -B -']
p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
p.stdin.write(source.decode('utf-8'));p.stdin.close();count=0;last=None
with output.open('x',encoding='utf-8') as f:
    for line in p.stdout:
        row=json.loads(line);wrapped={'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'board':row};f.write(json.dumps(wrapped)+'\n');f.flush();count+=1;last=row
        if row.get('event') in ('READY','TURN_COMPLETED','FINISHED'):print(json.dumps(wrapped),flush=True)
stderr=p.stderr.read();code=p.wait(timeout=8)
value={'host_ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':code,'line_count':count,'final':last,'stderr_present':bool(stderr),'names_transcripts_audio_or_vectors_saved':False}
with result.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')
if code:print(json.dumps({'monitor_error':True,'exit_code':code,'stderr_present':bool(stderr)}))
raise SystemExit(code)
