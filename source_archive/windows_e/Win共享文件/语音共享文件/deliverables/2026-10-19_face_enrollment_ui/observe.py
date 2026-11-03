"""Metadata-only observation of live independent face ownership and UI health."""
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=20)
parser.add_argument('--output',default='live_observation.json');args=parser.parse_args()
assert 1<=args.seconds<=45 and Path(args.output).name==args.output
remote=r'''
import json,time,urllib.request
from pathlib import Path
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
rows=[];start=time.monotonic()
while time.monotonic()-start<SECONDS:
 health=get(8790,'/health');state=get(8790,'/v1/ui/status');identity=state['modules']['identity']
 detail=identity.get('detail','') if identity['state']!='KNOWN' else 'KNOWN_NAME_REDACTED'
 rows.append({'seconds':round(time.monotonic()-start,2),'pid':health['pid'],'target_kind':identity.get('target_kind'),
  'face_count':identity.get('face_count'),'face_target':identity.get('face_target'),'body_target':state['modules']['target'].get('selected'),
  'identity_state':identity['state'],'identity_detail':detail,'can_enroll':state['capabilities']['identity_enroll'],
  'has_face_preview':bool(identity.get('face_preview')),'database_revision':identity['db_version'],
  'registered_count':len(identity['people']),'identity_health':health['identity'],
  'capture_hz':health['capture_hz'],'detection_hz':health['detection_hz'],'capture_age_ms':health['capture_age_ms'],
  'camera_error':health['camera_error'],'detector_error':health['detector_error']})
 time.sleep(.4)
ui=get(8783,'/api/state')
result={'samples':rows,'ui_phase':ui['phase'],'automatic':ui['automatic_conversation'],
 'known_samples':sum(r['identity_state']=='KNOWN' for r in rows),'face_target_samples':sum(bool(r['face_target']) for r in rows),
 'enrollable_samples':sum(r['can_enroll'] for r in rows),'photos_saved':False,'templates_exported':False,'names_exported':False}
print(json.dumps(result))
'''.replace('SECONDS',str(args.seconds),1)
result=json.loads(ssh('python3 -B -',remote,timeout=args.seconds+25))
(HERE/args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:value for key,value in result.items() if key!='samples'},ensure_ascii=True))
if result['samples']:print(json.dumps({'first':result['samples'][0],'last':result['samples'][-1]},ensure_ascii=True))
