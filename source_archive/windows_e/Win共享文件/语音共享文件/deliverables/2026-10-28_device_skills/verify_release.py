"""Read-only final integrity, ownership and state verification."""
import base64,hashlib,json,sys,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path[:0]=[str(A),str(H.parent/'2026-10-18_board_dialogue')]
from board_ssh import ssh
from common.voice_service_capabilities import SERVICE_REVISION,source_fingerprint,require_current_voice
c=json.loads((H/'candidate.json').read_text());base=json.loads((H/'baseline.json').read_text())
test_sources={p.relative_to(A).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (A/'tests/framework').glob('*.py')}
script=r'''
import base64,hashlib,json,subprocess,urllib.request
from pathlib import Path
c=CANDIDATE;b=BASE;r=Path(c['runtime'])/'aura'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==c['boot']
assert c['startup'] in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
pins=json.loads((Path(c['startup'])/'config.json').read_text())['component_sha256']
assert pins==c['pins']
for n,sha in pins.items():assert hashlib.sha256((r/n).read_bytes()).hexdigest()==sha,n
unchanged=[];test_refreshes={}
for n,sha in b['source_sha256'].items():
 if n not in c['changes']:
  actual=hashlib.sha256((r/n).read_bytes()).hexdigest()
  if actual!=sha:
   # prepare_board.py explicitly copied the project's framework tests.
   # Permit only those exact test bytes; every runtime source still must match.
   assert n.startswith('tests/framework/') and TEST_SOURCES.get(n)==actual,n
   test_refreshes[n]={'baseline':sha,'deployed':actual}
  else:unchanged.append(n)
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:s=json.load(f)
assert s['phase']=='IDLE' and s['audio_output_state']=='IDLE_READY' and not s.get('error')
assert not s['handsfree_dialogue']['enabled'] and not s['handsfree_dialogue']['microphone_open']
assert s['handsfree_dialogue']['entry_mode']=='wake_word' and s['handsfree_dialogue']['visual_required'] is False
assert not s['manual_pan']['automatic_following'] and s['manual_pan']['state']=='FAULT' and s['manual_pan']['pulse_us'] is None
assert s['ui_settings']['volume']==70 and not s['ui_settings']['muted']
assert s['portrait_offload']['mode']=='remote' and s['portrait_offload']['target_fps']==16
camera=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()
assert camera=='1333'
print(json.dumps({'boot':c['boot'],'runtime':c['runtime'],'pins_verified':len(pins),
 'unchanged_python':len(unchanged),'refreshed_test_files':test_refreshes,'camera_pid':camera,'phase':s['phase'],'audio_output_state':s['audio_output_state'],
 'handsfree_dialogue':s['handsfree_dialogue'],'manual_pan':{k:s['manual_pan'].get(k) for k in ('state','pulse_us','automatic_following')},
 'mixer':{k:s['ui_settings'][k] for k in ('volume','muted')},'device_observer':s.get('device_observer'),
 'portrait_offload':s['portrait_offload'],'avatar_display':s['avatar_display'],
 'board_sources':{n:base64.b64encode((r/n).read_bytes()).decode() for n in c['changes']}}))
'''.replace('CANDIDATE',repr(c)).replace('BASE',repr(base)).replace('TEST_SOURCES',repr(test_sources))
v=json.loads(ssh('python3 -B -',script,timeout=30))
for n,encoded in v.pop('board_sources').items():
 p=H/'board_deployed_source'/n;p.parent.mkdir(parents=True,exist_ok=True);raw=base64.b64decode(encoded)
 assert hashlib.sha256(raw).hexdigest()==c['pins'][n]
 p.write_bytes(raw)
with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=5) as f:health=json.load(f)
config=json.loads((A/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
require_current_voice(health,config['model'],source_fingerprint(A));assert not health['busy']
v['host']={'ready':True,'revision':health['service_revision'],'source_fingerprint':health['source_fingerprint'],
 'face_features_ready':health['identity_features']['ready'],'automatic_speaker_unlock':health['profile_access']['automatic_speaker_unlock']}
for name,port in [('device_hub',8812),('visual_model',8810)]:
 with urllib.request.urlopen('http://127.0.0.1:%d/health'%port,timeout=5) as f:v[name]=json.load(f)
expected=json.loads((H/'windows_applied.json').read_text())
for n,row in expected.items():
 actual=hashlib.sha256((A/n).read_bytes()).hexdigest();candidate=hashlib.sha256((H/'candidate_source'/n).read_bytes()).hexdigest()
 assert actual==candidate,n
 row['final']=actual
v['host_files']=expected;v['status']='PASS'
(H/'release_verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v[k] for k in ('status','runtime','pins_verified','unchanged_python','camera_pid','phase','host')}))
