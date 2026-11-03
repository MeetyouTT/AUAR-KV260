"""Read-only verification of the committed display release and preserved state."""
import datetime
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-18_board_dialogue'))
from board_ssh import ssh

c = json.loads((HERE / 'candidate.json').read_text(encoding='utf-8'))
script = r'''
import hashlib,importlib.util,json,subprocess,urllib.request
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime']);stage=Path(c['stage'])
assert (stage/'committed').is_file()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==c['boot']
effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
assert c['startup']+'/launcher.py' in effective
cfg=json.loads((Path(c['startup'])/'config.json').read_text())
for rel,digest in cfg['component_sha256'].items():
    assert hashlib.sha256((root/'aura'/rel).read_bytes()).hexdigest()==digest,rel
assert hashlib.sha256((root/'aura/tools/board_avatar_gtk.py').read_text().encode()).hexdigest()==c['gui_text_sha256']
unchanged=0
for package in ('tools','board','common','host'):
    for p in (Path(c['previous_candidate']['runtime'])/'aura'/package).rglob('*.py'):
        rel=p.relative_to(Path(c['previous_candidate']['runtime'])/'aura')
        if rel.as_posix()=='tools/board_avatar_gtk.py':continue
        assert p.read_bytes()==(root/'aura'/rel).read_bytes(),str(rel)
        unchanged+=1
ui=json.loads((root/'aura/config/board_avatar_gtk.json').read_text())
assert ui['portrait_offload']['fps']==16 and ui['stable_avatar_fps']==16
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5) as f:s=json.load(f)
p=s['manual_pan'];h=s['handsfree_dialogue'];o=s['portrait_offload']
assert s['phase']=='IDLE' and s['audio_output_state']=='IDLE_READY' and not s.get('error') and not s.get('playing')
assert p['automatic_following'] is False and p['state']=='READY' and not p.get('readback',{}).get('active')
assert p['pulse_us']==PAN_EXPECTED and h['enabled'] is False and not h.get('microphone_open')
assert o['mode']=='remote' and o['target_fps']==16
assert s['ui_settings']['volume']==70 and s['ui_settings']['muted'] is False
assert s['local_transcription']['service']['profile_memory']['mode']=='guest'
assert s['avatar_display']['kind']=='native_sink_handoff' and s['avatar_display']['age_ms']<1000
print(json.dumps({'status':'PASS','runtime':str(root),'boot':c['boot'],'core_python_files_unchanged':unchanged,
 'gui_text_sha256':c['gui_text_sha256'],'startup_pins_verified':len(cfg['component_sha256']),
 'persistent_fps':16,'portrait_mode':o['mode'],'display':s['avatar_display'],
 'phase':s['phase'],'audio_output_state':s['audio_output_state'],'volume':70,'muted':False,
 'automatic_following':False,'motor_active':False,'pan_us':p['pulse_us'],
 'listener_enabled':False,'microphone_open':False,'profile_mode':'guest','actions_performed':[]}))
'''.replace('CANDIDATE', repr(c)).replace('PAN_EXPECTED', repr(json.loads((HERE/'follow_pause.json').read_text(encoding='utf-8'))['pan_after_us']))
v = json.loads(ssh('python3 -B -', script, timeout=25))
v['checked_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
(HERE / 'final_verification.json').write_text(json.dumps(v, indent=2), encoding='utf-8')
print(json.dumps(v))
