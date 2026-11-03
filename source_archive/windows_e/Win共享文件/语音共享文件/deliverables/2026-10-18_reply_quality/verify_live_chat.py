"""Observe one new real recording and playback ACK; never generates either."""
import argparse,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
sys.path.insert(0,str(ROOT/'aura'))
from board_ssh import ssh
from common.spoken_input import prepare_spoken_input
from common.reply_quality import possible_question_echo
parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=45);args=parser.parse_args()
assert 1<=args.seconds<=50
baseline=json.loads((HERE/'board_preflight.json').read_text(encoding='utf-8'))
config={'seconds':args.seconds,'request':baseline['transcription'].get('request_id'),
        'camera_pid':baseline['camera']['pid'],'boot':baseline['camera']['board_boot_id']}
script='config='+repr(config)+'\n'+r'''
import json,time,urllib.request
def get(port,path):
 with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as r:return json.load(r)
deadline=time.monotonic()+config['seconds'];result={'status':'WAITING_FOR_FRESH_CHAT'}
while time.monotonic()<deadline:
 s=get(8783,'/api/state');tr=s['local_transcription'];request=tr.get('request_id')
 ack=tr.get('service',{}).get('last_playback_ack') or {}
 if request and request!=config['request'] and tr['state']=='ANSWERED' and ack.get('request_id')==request and ack.get('committed'):
  turn=s['turns'][-1];capture=s['local_recording']['result'];camera=get(8790,'/health')
  assert capture['capture_id']==tr['capture_id'] and turn['audio_complete']
  assert not s.get('error') and not tr.get('error')
  assert turn['thinking_mode']=='chat' and not turn['thinking_feedback']
  assert turn['server_metrics']['clauses']==1
  assert camera['pid']==config['camera_pid'] and camera['board_boot_id']==config['boot']
  result={'status':'PASS_FRESH_CHAT_PLAYBACK','transcript':tr['text'],'capture':capture,'turn':turn,
          'playback_ack':ack,'camera_preserved':True,'camera_pid':camera['pid'],'board_boot_id':camera['board_boot_id'],
          'acoustic_onset_measured':False,'user_listening_accepted':None}
  break
 time.sleep(.2)
print(json.dumps(result))
'''
report=json.loads(ssh('python3 -',script,timeout=args.seconds+8))
if report['status'].startswith('PASS_'):
    llm=report['turn']['server_metrics']['timing']['llm']
    interpreted=prepare_spoken_input(report['transcript'])['text']
    assert llm['input_sha256']==hashlib.sha256(interpreted.encode()).hexdigest()
    assert llm['quality_retry_count'] in (0,1) and not llm['possible_question_echo']
    assert not possible_question_echo(interpreted,report['turn']['text'])
    name='live_playback.json'
else:name='live_pending.json'
(HERE/name).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
