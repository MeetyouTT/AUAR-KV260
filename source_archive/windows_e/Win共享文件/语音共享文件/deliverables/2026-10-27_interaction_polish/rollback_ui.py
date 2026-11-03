"""Check the retained original UI; --apply removes only this release's override."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-18_board_dialogue'))
from board_ssh import ssh

c = json.loads((HERE / 'candidate.json').read_text(encoding='utf-8'))
apply = '--apply' in sys.argv
script = r'''
import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
c=CANDIDATE;apply=APPLY;stage=Path(c['stage'])
drop=Path('/etc/systemd/system/aura-avatar-ui.service.d/'+'z'*32+'-aura-windows-portrait.conf')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==c['boot']
assert drop.is_file() and c['startup']+'/launcher.py' in drop.read_text()
assert c['startup'] in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
for rel,digest in c['unchanged_python_sha256'].items():
    assert hashlib.sha256((Path(c['source_runtime'])/'aura'/rel).read_bytes()).hexdigest()==digest,rel
assert hashlib.sha256((Path(c['source_runtime'])/'aura/config/pan_manual.local.json').read_bytes()).hexdigest()==c['original_pan_sha256']
def get():
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:return json.load(f)
before=get();pan=before['manual_pan'];hf=before['handsfree_dialogue']
assert before['phase']=='IDLE' and before['audio_output_state']=='IDLE_READY' and not before.get('playing')
assert hf['enabled'] is False and not hf.get('microphone_open')
assert pan['automatic_following'] is False and pan['state'] not in ('MOVING','STOPPING') and not pan.get('readback',{}).get('active')
report={'status':'CHECK_ONLY','apply_requested':apply,'own_override':str(drop),'original_runtime':c['source_runtime'],
        'pan_us_before':pan['pulse_us'],'monitor_enabled':False,'follow_resume_requested':False}
if apply:
    saved=drop.read_text();subprocess.run(['systemctl','stop','aura-avatar-ui.service'],check=True,capture_output=True,timeout=45)
    assert drop.read_text()==saved
    drop.unlink();subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=20)
    subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,capture_output=True,timeout=20)
    until=time.monotonic()+110
    while time.monotonic()<until:
        try:
            s=get();p=s['manual_pan'];h=s['handsfree_dialogue']
            if s['phase']=='IDLE' and s['audio_output_state']=='IDLE_READY' and not s.get('error'):
                assert h['enabled'] is False and not h.get('microphone_open')
                assert p['automatic_following'] is False and p['pulse_us']==pan['pulse_us']
                assert c['source_runtime'] in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
                report.update(status='ROLLED_BACK',pan_us_after=p['pulse_us']);break
        except (OSError,ValueError):pass
        time.sleep(.5)
    else:raise TimeoutError('Original UI readiness requires inspection; own override already removed')
print(json.dumps(report))
'''.replace('CANDIDATE', repr(c)).replace('APPLY', repr(apply))
compile(script, '<rollback-ui>', 'exec')
value = json.loads(ssh('python3 -B -', script, timeout=175 if apply else 25))
(HERE / ('rollback_applied.json' if apply else 'rollback_check.json')).write_text(json.dumps(value, indent=2), encoding='utf-8')
print(json.dumps(value))
