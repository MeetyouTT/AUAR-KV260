"""Watch the user's formal update; keep only counts, pose/score diagnostics and codes."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import json,time,urllib.request
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
until=time.monotonic()+40;rows=[];previous=None;turns={};pose=None;scores=[];known=0
while time.monotonic()<until:
 h=get(8790,'/health');i=get(8790,'/v1/ui/status')['modules']['identity'];u=get(8783,'/api/state')
 diag=h['identity']['sampling_diagnostics'];sample=i.get('enrollment_sampling',{})
 assert diag['template_policy']=='frontal_medoid_v1'
 m=diag['metrics']
 if m.get('candidate_pose'):pose=m['candidate_pose']
 if m.get('recent_validation'):scores=m['recent_validation']
 op=i.get('last_operation',{});operation={k:op.get(k) for k in ('action','state','db_version')}
 operation['original_identity_update']=op.get('detail','').startswith('已更新登记')
 row={'stage':sample.get('stage'),'counts':sample.get('counts'),'db_version':i['db_version'],
  'identity_count':len(i['people']),'identity_state':i['state'],'face_count':i.get('face_count'),
  'voice_stage':u['local_transcription']['service'].get('voice_enrollment',{}).get('stage'),
  'last_operation':operation,'failure':diag.get('last_failure')}
 signature=json.dumps(row,sort_keys=True)
 if signature!=previous:rows.append(row);previous=signature
 for t in u.get('turns',[]):
  llm=t.get('server_metrics',{}).get('timing',{}).get('llm',{})
  turns[str(t['generation'])]={'backend':llm.get('backend'),'code':llm.get('identity_reply_code'),
    'audio_complete':t.get('audio_complete')}
 if i['db_version']>14 and i['state']=='KNOWN':known+=1
 committed=operation['action']=='identity_enroll' and operation['state']=='COMMITTED' and operation['db_version']>14
 registered_audio=any(t['code']=='registered' and t['audio_complete'] for t in turns.values())
 if committed and registered_audio:break
 time.sleep(.2)
print(json.dumps({'status':'FORMAL_UPDATE_COMMITTED_AND_AUDIO_COMPLETE' if committed and registered_audio else 'WAITING_FOR_FORMAL_UPDATE',
 'observations':rows[-128:],'turn_codes':turns,'last_candidate_pose':pose,
 'last_validation_scores':scores,'updated_identity_known_samples':known,
 'database_revision':i['db_version'],'identity_count':len(i['people']),
 'last_operation':operation,'registered_audio_complete':registered_audio,
 'automatic':u['automatic_conversation'],'photos_templates_names_or_transcripts_exported':False,
 'database_commands_issued_by_observer':False}))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=55))
path=HERE/'update_observation.json'
if path.exists():
 old=json.loads(path.read_text(encoding='utf-8'))
 r['earlier_observation']=old
path.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k not in ('observations','earlier_observation','last_validation_scores')},ensure_ascii=True))
