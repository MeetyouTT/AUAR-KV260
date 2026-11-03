"""Pause only at natural idle; independently restore user's prior monitor choice."""
import base64,json,sys,datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'action_candidate.json').read_text());mode=sys.argv[1]
restore=r'''
import json,urllib.request,time,subprocess
from pathlib import Path
p=Path(STAGE)
if (p/'pc-monitor-restored').exists():raise SystemExit(0)
expected=json.loads((p/'pc-monitor-before.json').read_text())['enabled']
def get():return json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5))
state=get()
if state['handsfree_dialogue']['enabled']!=expected:
 req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=b'{"type":"conversation_toggle"}',headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 json.load(urllib.request.urlopen(req,timeout=5))
 time.sleep(1)
assert get()['handsfree_dialogue']['enabled']==expected,'Monitor restore failed'
(p/'pc-monitor-restored').write_text('restored')
print(json.dumps({'monitor_restored':True,'enabled':expected}))
'''.replace('STAGE',repr(c['stage']),1)
if mode=='pause':
 remote=r'''
import json,time,subprocess,urllib.request,base64
from pathlib import Path
p=Path(STAGE);assert (p/'committed').is_file(),'Action UI not committed'
def get():return json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5))
s=get();h=s['handsfree_dialogue'];tx=s['local_transcription'];svc=tx['service'];ack=svc.get('last_playback_ack') or {}
assert s['phase']=='IDLE' and not s['playing'] and not s['paused'] and not svc.get('pending')
assert not (h.get('microphone_open') and s.get('automatic_conversation',{}).get('speech_active'))
assert not h.get('listening_timing',{}).get('holding_utterance') and not s.get('voice_barge_in',{}).get('next_utterance_pending')
assert not (tx['state']=='ANSWERED' and (ack.get('request_id')!=tx.get('request_id') or not ack.get('committed')))
assert tx['state'] not in ('GENERATING','PLAYING','TRANSCRIBING')
assert s.get('manual_pan',{}).get('state') not in ('MOVING','STOPPING')
(p/'pc-monitor-before.json').write_text(json.dumps({'enabled':h['enabled']}))
restore=p/'restore-pc-monitor.py';restore.write_bytes(base64.b64decode(RESTORE))
subprocess.run(['systemd-run','--unit=aura-motion-pc-monitor-'+p.name,'--on-active=420','/usr/bin/python3','-B',str(restore)],check=True,capture_output=True,timeout=20)
if h['enabled']:
 req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=b'{"type":"conversation_toggle"}',headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 json.load(urllib.request.urlopen(req,timeout=5));time.sleep(1)
s=get();assert not s['handsfree_dialogue']['enabled'] and not s['handsfree_dialogue']['microphone_open']
print(json.dumps(dict(phase=s['phase'],enabled=False,playing=s['playing'],pending=s['local_transcription']['service']['pending'],original_enabled=h['enabled'])))
'''.replace('STAGE',repr(c['stage']),1).replace('RESTORE',repr(base64.b64encode(restore.encode()).decode()),1)
elif mode=='refresh':
 remote=r'''
import json,urllib.request
from pathlib import Path
p=Path(STAGE)
s=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5))
assert s['phase']=='IDLE' and not s['playing'] and not s['handsfree_dialogue']['enabled'] and not s['local_transcription']['service']['pending']
print(json.dumps(dict(phase=s['phase'],enabled=False,playing=False,pending=False,original_enabled=json.loads((p/'pc-monitor-before.json').read_text())['enabled'])))
'''.replace('STAGE',repr(c['stage']),1)
else:
 remote=restore+"\nsubprocess.run(['systemctl','stop','aura-motion-pc-monitor-'+p.name+'.timer'],capture_output=True,timeout=20)\n"
r=json.loads(ssh('python3 -B -',remote,timeout=35));r['checked_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(HERE/('pc_action_board_guard.json' if mode in ('pause','refresh') else 'pc_action_monitor_restored.json')).write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps(r))
