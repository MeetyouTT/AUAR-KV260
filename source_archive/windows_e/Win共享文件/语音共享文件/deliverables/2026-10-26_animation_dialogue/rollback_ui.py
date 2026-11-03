"""Explicit idle/guest-only return to the preserved UI. Not run during delivery."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh

def main():
    c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
    script=r'''
import json,subprocess,time,urllib.request
from pathlib import Path
c=CANDIDATE;stage=Path(c['stage'])
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==c['boot'],'Re-check changed boot first'
drop=Path('/etc/systemd/system/aura-avatar-ui.service.d')/('z'*30+'-aura-animation-dialogue.conf')
assert drop.is_file() and str(stage) in drop.read_text(),'Own override was changed or absent'
def get():
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:return json.load(f)
s=get();assert s['phase']=='IDLE' and s['audio_output_state']=='IDLE_READY'
assert not s.get('playing') and not s.get('streaming_reply')
assert s['local_transcription']['service']['profile_memory']['mode']=='guest','Release personal selection before rollback'
assert s['handsfree_dialogue']['enabled'] is False and not s['handsfree_dialogue'].get('microphone_open')
assert s.get('manual_pan',{}).get('state') not in ('MOVING','STOPPING')
preference=Path('/root/.local/share/aura/handsfree_dialogue.json');before=preference.read_bytes()
(stage/'committed_override_backup.conf').write_bytes(drop.read_bytes())
subprocess.run(['systemctl','stop','aura-avatar-ui.service'],check=True,capture_output=True,timeout=45)
drop.unlink();subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=20)
subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,capture_output=True,timeout=20)
deadline=time.monotonic()+110
while True:
    try:
        s=get()
        if s.get('phase')=='IDLE' and s.get('audio_output_state')=='IDLE_READY':break
    except Exception:pass
    if time.monotonic()>deadline:raise TimeoutError('Original UI readiness failed; inspect service journal')
    time.sleep(.5)
assert preference.read_bytes()==before
effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
assert str(stage) not in effective
result={'status':'ROLLED_BACK_BY_EXPLICIT_COMMAND','removed_override':str(drop),'effective_entry':effective,'preference_preserved':True}
(stage/'explicit_rollback.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('CANDIDATE',repr(c))
    compile(script,'<explicit-ui-rollback>','exec')
    print(ssh('python3 -B -',script,timeout=190))

if __name__=='__main__':main()
