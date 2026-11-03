"""Observe identity lifecycle/latency without exporting names, photos or templates."""
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=20)
parser.add_argument('--output',default='live_observation.json');parser.add_argument('--show-vision',action='store_true')
args=parser.parse_args();assert 1<=args.seconds<=50 and Path(args.output).name==args.output
remote=r'''
import hashlib,json,statistics,time,urllib.request
from pathlib import Path
seconds=SECONDS
def get(port,path):return json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
if SHOW_VISION:
 req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps({'type':'ui_page','page':'vision'}).encode(),
  headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 with urllib.request.urlopen(req,timeout=6) as r:page_command=json.load(r)
else:page_command=None
rows=[];errors=[];start=time.monotonic()
while time.monotonic()-start<seconds:
 try:
  h=get(8790,'/health');s=get(8790,'/v1/ui/status');i=s['modules'].get('identity',{});t=s['modules'].get('target',{})
  op=i.get('last_operation',{});pid=h['pid'];proc=Path('/proc/%d/stat'%pid).read_text().split()
  row={'seconds':round(time.monotonic()-start,2),'identity_state':i.get('state'),
   'person_hash':hashlib.sha256(i.get('person_id','').encode()).hexdigest()[:16] if i.get('person_id') else '',
   'people_count':h.get('people_count'),'enrolled_count':len(i.get('people',[])),
   'can_enroll':s['capabilities'].get('identity_enroll'),'can_delete':s['capabilities'].get('identity_delete'),
   'target':t.get('selected'),'capture_age_ms':h.get('capture_age_ms'),'observation_age_ms':h.get('observation_age_ms'),
   'capture_hz':h.get('capture_hz'),'detection_hz':h.get('detection_hz'),'preview_hz':h.get('preview_hz'),
   'identity':h.get('identity',{}),'identity_detail':i.get('detail','') if i.get('state')!='KNOWN' and not op else '',
   'operation':{k:op.get(k) for k in ('command_id','action','state','db_version')} if op else None,
   'camera_error':h.get('camera_error'),'detector_error':h.get('detector_error'),
   'pid':pid,'cpu_ticks':int(proc[13])+int(proc[14]),'rss_pages':int(proc[23])}
  rows.append(row)
 except Exception as ex:errors.append(type(ex).__name__+': '+str(ex))
 time.sleep(.5)
ui=get(8783,'/api/state')
result={'samples':rows,'errors':errors,'page_command':page_command,'ui_phase':ui.get('phase'),'ui_page':ui.get('ui_page'),
 'automatic':ui.get('automatic_conversation'),'recording_state':ui.get('local_recording',{}).get('state'),
 'names_exported':False,'photos_saved':False,'templates_exported':False,
 'known_samples':sum(r['identity_state']=='KNOWN' for r in rows),'enrollable_samples':sum(bool(r['can_enroll']) for r in rows)}
print(json.dumps(result))
'''.replace('SECONDS',str(args.seconds)).replace('SHOW_VISION',repr(args.show_vision))
r=json.loads(ssh('python3 -',remote,timeout=args.seconds+25))
(HERE/args.output).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k!='samples'},ensure_ascii=True))
if r['samples']:print(json.dumps({'first':r['samples'][0],'last':r['samples'][-1]},ensure_ascii=True))
