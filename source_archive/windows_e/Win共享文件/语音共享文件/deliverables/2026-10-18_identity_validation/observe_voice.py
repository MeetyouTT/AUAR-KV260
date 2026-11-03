"""Observe oral enrollment and playback ACKs; redact spoken names in evidence."""
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=40)
parser.add_argument('--output',default='live_voice_enrollment.json');args=parser.parse_args()
assert 1<=args.seconds<=50 and Path(args.output).name==args.output
remote=r'''
import hashlib,json,time,urllib.request
def get(port,path):return json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
def phrase(text):
 if '登记成功' in text:return 'registered'
 if '要保存人脸特征' in text:return 'confirm_name_prompt'
 if '你希望我怎么称呼你' in text:return 'ask_name_prompt'
 if '没有确认登记成功' in text:return 'failed'
 if '登记已取消' in text:return 'cancelled'
 if any(x in text for x in ('我叫','叫我','我的名字是')):return 'spoken_name_redacted'
 if '确认登记' in text:return 'confirm_or_retry'
 if '登记身份' in text:return 'request_enrollment'
 return 'other'
start=time.monotonic();rows=[];rounds={};errors=[];previous=None
while time.monotonic()-start<SECONDS:
 try:
  ui=get(8783,'/api/state');cam=get(8790,'/v1/ui/status');tx=ui['local_transcription'];svc=tx['service'];identity=cam['modules'].get('identity',{})
  op=identity.get('last_operation',{});req=tx.get('request_id');turns=ui.get('turns',[])
  row={'seconds':round(time.monotonic()-start,2),'automatic':ui.get('automatic_conversation'),
   'recording':ui['local_recording']['state'],'transcription_state':tx.get('state'),
   'request_id':req,'flow':svc.get('voice_enrollment'),'identity_state':identity.get('state'),
   'enrolled_count':len(identity.get('people',[])),
   'person_hash':hashlib.sha256(identity.get('person_id','').encode()).hexdigest()[:16] if identity.get('person_id') else '',
   'target':cam['modules']['target'].get('selected'),
   'operation':{k:op.get(k) for k in ('command_id','action','state','db_version')} if op else None}
  signature=json.dumps({k:v for k,v in row.items() if k!='seconds'},sort_keys=True)
  if signature!=previous:rows.append(row);previous=signature
  if req:
   item=rounds.setdefault(req,{'request_id':req})
   text=tx.get('text') or ''
   if text:item.update(transcript_kind=phrase(text),transcript_sha256=hashlib.sha256(text.encode()).hexdigest())
   ack=svc.get('last_playback_ack') or {}
   if ack.get('request_id')==req:item['ack']=ack
   if tx.get('state')=='ANSWERED' and turns:
    turn=turns[-1];item.update(reply_kind=phrase(turn.get('text','')),audio_complete=turn.get('audio_complete'),
     software_request_to_answer_seconds=turn.get('request_to_answer_seconds'))
  if tx.get('state')=='ERROR':errors.append(tx.get('error'))
 except Exception as ex:errors.append(str(ex))
 time.sleep(.15)
print(json.dumps({'transitions':rows,'rounds':rounds,'errors':sorted(set(errors)),
 'names_redacted':True,'photos_saved':False,'templates_exported':False,'synthetic_audio_injected':False}))
'''.replace('SECONDS',str(args.seconds))
r=json.loads(ssh('python3 -',remote,timeout=args.seconds+25))
(HERE/args.output).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'rounds':r['rounds'],'errors':r['errors'],'first':r['transitions'][0] if r['transitions'] else None,
 'last':r['transitions'][-1] if r['transitions'] else None},ensure_ascii=True))
