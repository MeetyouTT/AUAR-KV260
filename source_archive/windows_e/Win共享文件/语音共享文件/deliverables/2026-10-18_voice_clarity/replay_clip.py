"""Replay only prepared diagnostic clips on an idle board."""
import argparse,json,sys
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
p=argparse.ArgumentParser();p.add_argument('--clip',choices=['same_pcm_leadin_500ms.wav','same_pcm_leadin_1000ms.wav','two_identical_sentences_one_stream.wav','converted_48k_stereo.wav'],required=True);p.add_argument('--delay',type=int,default=15);a=p.parse_args()
assert 0<=a.delay<=20
s=r'''
import subprocess,json,urllib.request,time
from pathlib import Path
p=PARAMS
time.sleep(p['delay'])
u=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3))
assert u['phase']=='IDLE' and not u['playing'] and u['local_recording']['state']!='RECORDING' and not u['local_transcription']['service']['pending'],'Board busy'
assert not u['ui_settings']['muted'],'Board muted'
file=Path('/home/root/aura-audio-clarity-20261018')/p['clip']
r=subprocess.run(['aplay','-q','-D','hw:CARD=MCP01,DEV=0','-B','200000','-F','20000',str(file)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15,universal_newlines=True)
print(json.dumps({'clip':p['clip'],'returncode':r.returncode,'output':r.stdout}))
'''.replace('PARAMS',repr(vars(a)))
v=json.loads(ssh('python3 -',s,timeout=45));v['host_utc']=datetime.now(timezone.utc).isoformat()
with (HERE/'replays.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(v,ensure_ascii=False)+'\n')
print(json.dumps(v))
