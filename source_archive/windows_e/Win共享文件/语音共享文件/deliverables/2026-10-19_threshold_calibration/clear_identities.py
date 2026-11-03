"""User-authorized delete-all via live identity API; no database backup/export."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import hashlib,json,sqlite3,time,urllib.request,uuid
from pathlib import Path
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
ui=get(8783,'/api/state');assert ui['phase']=='IDLE' and not ui['automatic_conversation']['enabled']
assert ui['local_recording']['state']!='RECORDING' and not ui['local_transcription']['service']['pending']
h=get(8790,'/health');s=get(8790,'/v1/ui/status');identity=s['modules']['identity']
args=Path('/proc/%d/cmdline'%h['pid']).read_bytes().decode().split('\0')
camera=json.loads(Path(args[args.index('--config')+1]).read_text())
config_path=Path(camera['identity']['config']);config_raw=config_path.read_bytes();cfg=json.loads(config_raw)
db=Path(cfg['database']).expanduser()
def counts():
 with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as connection:
  return {'identities':connection.execute('SELECT count(*) FROM identities').fetchone()[0],
          'templates':connection.execute('SELECT count(*) FROM templates').fetchone()[0],
          'revision':connection.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]}
before=counts();ids={p['person_id'] for p in identity['people']}
assert before['identities']==len(ids),'Hidden identities require inspection before delete-all'
session=uuid.uuid4().hex;receipts=[]
for index,person_id in enumerate(sorted(ids)):
 s=get(8790,'/v1/ui/status');item=s['modules']['identity']
 assert s['board_boot_id']==h['board_boot_id']
 assert {p['person_id'] for p in item['people']}<=ids,'Library changed during deletion'
 now=s['observed_mono_ms'];cid='user-delete-all-'+uuid.uuid4().hex
 command={'protocol_version':'aura-ui-1','board_boot_id':s['board_boot_id'],'service_epoch':s['service_epoch'],
  'command_id':cid,'ui_epoch':session,'ui_generation':0,'context':s['context'],
  'snapshot_sequence':s['sequence'],'issued_mono_ms':now,'deadline_mono_ms':now+2500,
  'action':'identity_delete','params':{'person_id':person_id,'db_version':item['db_version'],'confirmed':True}}
 request=urllib.request.Request('http://127.0.0.1:8790/v1/ui/commands',
  data=json.dumps(command).encode(),headers={'Content-Type':'application/json'},method='POST')
 ack=json.load(urllib.request.urlopen(request,timeout=4));assert ack['accepted'],ack.get('detail')
 latest=get(8790,'/v1/ui/status')['modules']['identity'];operation=latest.get('last_operation',{})
 assert operation.get('command_id')==cid and operation.get('action')=='identity_delete' and operation.get('state')=='COMMITTED'
 assert latest['db_version']==item['db_version']+1 and person_id not in {p['person_id'] for p in latest['people']}
 receipts.append({'index':index+1,'committed':True,'revision':latest['db_version']})
after=counts();assert after['identities']==after['templates']==0
assert after['revision']==before['revision']+len(ids)
time.sleep(.8);latest=get(8790,'/v1/ui/status')['modules']['identity']
assert latest['people']==[] and latest['state']!='KNOWN' and latest['enrollment_sampling']['stage']=='idle'
assert config_path.read_bytes()==config_raw
print(json.dumps({'client_date':'2026-10-19','authorization':'用户明确要求全部删除身份登记记录',
 'status':'ALL_IDENTITY_RECORDS_DELETED_AND_VERIFIED_EMPTY','before':before,'after':after,
 'committed_deletions':receipts,'live_registered_count':len(latest['people']),
 'live_identity_state':latest['state'],'sampling_stage':latest['enrollment_sampling']['stage'],
 'threshold':cfg['threshold'],'ambiguity_margin':cfg['ambiguity_margin'],
 'configuration_unchanged':True,'runtime_restarted':False,'database_backup_created':False,
 'photos_accessed':False,'names_exported':False,'templates_exported':False,
 'cached_results_invalidated_by_official_delete_api':True}))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=45))
(HERE/'delete_all_receipt.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=True))
