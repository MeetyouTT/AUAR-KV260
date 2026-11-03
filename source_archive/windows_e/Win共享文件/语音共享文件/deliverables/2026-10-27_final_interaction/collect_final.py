"""Read final native state and phase performance without touching devices."""
import json,sys,datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
script=r'''
import json,urllib.request,subprocess,hashlib
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime']);stage=Path(c['stage'])
assert c['startup'] in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==c['boot']
cfg=json.loads((Path(c['startup'])/'config.json').read_text())
for n,h in cfg['component_sha256'].items():assert hashlib.sha256((root/'aura'/n).read_bytes()).hexdigest()==h,n
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:s=json.load(f)
p=s['manual_pan'];h=s['handsfree_dialogue']
assert s['phase']=='IDLE' and s['audio_output_state']=='IDLE_READY' and not s['error']
assert h['enabled'] is False and not h.get('microphone_open')
assert p['state']=='FAULT' and p['automatic_following'] is False and p['pulse_us'] is None
assert p['error']=='Exact board/boot/firmware/VART context required; no MMIO' and not p.get('history')
assert s['portrait_offload']['mode']=='remote' and s['portrait_offload']['target_fps']==16
assert s['ui_settings']['volume']==70 and s['ui_settings']['muted'] is False
assert s['local_transcription']['service']['profile_memory']['mode']=='guest'
log=Path(s['avatar_renderer']['presentation']['performance_log']['path'])
assert log.is_relative_to(root/'managed-runs')
logs=[p for p in (log.with_name(log.name+'.1'),log) if p.exists()]
records=[json.loads(line) for p in logs for line in p.read_text().splitlines() if line.strip()]
speaking=[r for r in records if any(p['phase']=='SPEAKING' for p in r['phases'])]
assert speaking,'No real speaking performance evidence'
for r in speaking:
 for phase in r['phases']:
  assert phase['target_fps'] in (8,16) and phase['long_frame_budget_ms']==1500/phase['target_fps']
print(json.dumps({'status':'PASS','boot':c['boot'],'runtime':c['runtime'],'display':s['avatar_display'],
'portrait':s['portrait_offload'],'mechanical_state':s['manual_pan']['state'],
'mechanical_error':s['manual_pan']['error'],'following':False,'microphone':False,
'audio':s['audio_output_state'],'volume':s['ui_settings']['volume'],'muted':False,'profile':'guest',
'component_hashes_verified':len(cfg['component_sha256']),'performance_log_sources':[str(p) for p in logs],
'speaking_performance_records':speaking}))
'''.replace('CANDIDATE',repr(c))
v=json.loads(ssh('python3 -B -',script,timeout=25));v['checked_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(HERE/'final_state.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in v.items() if k not in ('speaking_performance_records','portrait')}))

