"""Read-only bounded observation of real enrollment and photo archive progress."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

remote=r'''
import json,time,urllib.request
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
deadline=time.monotonic()+40;rows=[];previous=None;turns={}
while time.monotonic()<deadline:
 h=get(8790,'/health');i=get(8790,'/v1/ui/status')['modules']['identity'];u=get(8783,'/api/state')
 photo=h['identity']['enrollment_photos'];diag=h['identity']['sampling_diagnostics']
 sampling=i.get('enrollment_sampling',{})
 op=i.get('last_operation',{})
 row={'stage':sampling.get('stage'),'counts':sampling.get('counts'),
  'database_revision':i['db_version'],'identity_count':len(i['people']),
  'identity_state':i['state'],'face_count':i.get('face_count'),
  'voice_stage':u['local_transcription']['service'].get('voice_enrollment',{}).get('stage'),
  'archive':photo,'failure':diag.get('last_failure'),
  'operation':{k:op.get(k) for k in ('action','state','db_version')}}
 signature=json.dumps(row,sort_keys=True)
 if signature!=previous:rows.append(row);previous=signature
 for turn in u.get('turns',[]):
  llm=turn.get('server_metrics',{}).get('timing',{}).get('llm',{})
  turns[str(turn['generation'])]={'backend':llm.get('backend'),'code':llm.get('identity_reply_code'),
    'audio_complete':turn.get('audio_complete')}
 terminal=photo.get('latest_session') and photo.get('outcome') in ('committed','failed','cancelled','interrupted')
 if terminal:break
 time.sleep(.4)
print(json.dumps({'status':'REAL_ENROLLMENT_PHOTOS_AVAILABLE' if photo.get('image_count',0)>0 else 'WAITING_FOR_NEW_ENROLLMENT',
 'latest':row,'observations':rows[-128:],'turn_codes':turns,
 'database_commands_issued_by_observer':False,'photos_names_embeddings_or_transcripts_exported':False}))
'''
result=json.loads(ssh('python3 -B -',remote,timeout=55))
(HERE/'photo_observation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='observations'},ensure_ascii=False))
