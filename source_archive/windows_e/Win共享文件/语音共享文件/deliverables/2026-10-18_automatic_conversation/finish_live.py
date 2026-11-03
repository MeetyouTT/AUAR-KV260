"""Honor the user's reported end; record any explicit cleanup separately."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import json,time,urllib.request
def get():return json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3))
before=get();deadline=time.monotonic()+10
while before['automatic_conversation']['enabled'] and before.get('playing') and time.monotonic()<deadline:
    time.sleep(.2);before=get()
command_sent=False
if before['automatic_conversation']['enabled']:
    request=urllib.request.Request('http://127.0.0.1:8783/api/command',json.dumps({'type':'event','event':'cancel'}).encode(),
         {'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
    with urllib.request.urlopen(request,timeout=4) as response:result=json.load(response)
    command_sent=True
deadline=time.monotonic()+10
while time.monotonic()<deadline:
    final=get()
    if not final['automatic_conversation']['enabled'] and final['phase']=='IDLE' and final['local_recording']['state']!='RECORDING' and not final['local_transcription']['service']['pending']:break
    time.sleep(.2)
else:raise RuntimeError('Reported end did not settle')
print(json.dumps({'status':'STOPPED','explicit_agent_cleanup':command_sent,'reason':'user reported 已说完并结束',
                  'before':before,'final':final}))
'''
result=json.loads(ssh('python3 -',remote,timeout=35))
(HERE/'final_stop_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':result['status'],'explicit_agent_cleanup':result['explicit_agent_cleanup']},ensure_ascii=True))
