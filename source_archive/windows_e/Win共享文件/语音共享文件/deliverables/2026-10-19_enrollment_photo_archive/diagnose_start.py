"""Read-only enrollment entry diagnostics without transcript/name/photo export."""
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import json,time,urllib.request,sys
from pathlib import Path
cfg=json.loads(Path('/home/root/aura-spoken-identity-routing-20261019/candidate-fa8e1697c110/startup/config.json').read_text())
sys.path.insert(0,str(Path(cfg['runtime'])/'aura'))
from board.interaction.ui_contract import validate_snapshot,millis
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
rows=[];deadline=time.monotonic()+8
while time.monotonic()<deadline:
 snapshot=get(8790,'/v1/ui/status');health=get(8790,'/health');ui=get(8783,'/api/state')
 identity=snapshot['modules']['identity'];service=ui['local_transcription']['service']
 cached=ui.get('ui_runtime',{});local_snapshot=cached.get('snapshot')
 try:
  validate_snapshot(local_snapshot,Path('/proc/sys/kernel/random/boot_id').read_text().strip(),millis());cache_error=''
 except (ValueError,KeyError,TypeError) as exc:cache_error=str(exc)
 row={'snapshot_age_ms':round(time.monotonic()*1000-snapshot['observed_mono_ms']),
  'snapshot_ttl_ms':snapshot['ttl_ms'],'service_epoch':snapshot['service_epoch'],
  'identity':{k:identity.get(k) for k in ('state','face_count','face_target','source_frame_id','source_mono_ms','face_preview')},
  'entry_capabilities':{k:snapshot['capabilities'].get(k) for k in ('identity_sample_start','identity_enroll')},
  'identity_health':health['identity'],'voice_enrollment':service.get('voice_enrollment'),
  'last_voice_route':service.get('last_voice_route'),'automatic':ui['automatic_conversation'],
  'ui_cache':{'link':cached.get('link'),'error':cached.get('error'),
    'validation_error':cache_error,'has_display_cancel_flag':bool(local_snapshot and local_snapshot.get('interaction_suppressed')),
    'source_age_ms':None if not local_snapshot else millis()-local_snapshot['observed_mono_ms']}}
 if identity['state']!='KNOWN':row['identity']['detail']=identity.get('detail')
 rows.append(row);time.sleep(.4)
turns=ui.get('turns',[])
print(json.dumps({'status':'ENROLLMENT_ENTRY_READ_ONLY_DIAGNOSIS','samples':rows,
 'turn_field_names':[sorted(t) for t in turns[-3:]],
 'last_transcription_field_names':sorted(ui.get('local_transcription',{})),
 'photos_names_embeddings_transcripts_exported':False}))
'''
result=json.loads(ssh('python3 -B -',remote,timeout=25))
(HERE/'entry_diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
rows=result['samples'];keys={json.dumps(row['identity']['face_target'],sort_keys=True) for row in rows}
print(json.dumps({'samples':len(rows),'can_start_samples':sum(bool(row['entry_capabilities']['identity_sample_start']) for row in rows),
 'distinct_face_targets':len(keys),'latest':rows[-1],
 'turn_field_names':result['turn_field_names'],'last_transcription_field_names':result['last_transcription_field_names']},ensure_ascii=False))
