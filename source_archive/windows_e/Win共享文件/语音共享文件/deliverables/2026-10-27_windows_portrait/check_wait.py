"""Read-only handoff check. Never stop follow, restart UI, or touch hardware."""
import datetime
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-18_board_dialogue'))
from board_ssh import ssh

SCRIPT = r'''
import json,re,shlex,subprocess,urllib.request
from pathlib import Path
effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True)
args=shlex.split(re.search(r'argv\[\]=(.*?);',effective).group(1))
config=Path(args[args.index('--config')+1]);runtime=Path(json.loads(config.read_text())['runtime'])
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as response:state=json.load(response)
pan=state.get('manual_pan',{});follow=pan.get('face_follow',{});readback=pan.get('readback',{})
pan_config=json.loads((runtime/'aura/config/pan_manual.local.json').read_text())
follow_config=pan_config.get('face_follow_config',{})
if isinstance(follow_config,str):
    follow_path=Path(follow_config)
    if not follow_path.is_absolute():follow_path=runtime/'aura'/follow_path
    follow_config=json.loads(follow_path.read_text())
hf=state.get('handsfree_dialogue',{});display=state.get('avatar_display',{})
reasons=[]
if pan.get('automatic_following') is not False:reasons.append('FOLLOW_ACTIVE_OR_UNKNOWN')
if pan.get('state') in ('MOVING','STOPPING') or readback.get('active'):reasons.append('MOTION_ACTIVE')
if state.get('phase')!='IDLE' or state.get('playing') or state.get('streaming_reply'):reasons.append('DIALOGUE_BUSY')
if state.get('audio_output_state')!='IDLE_READY':reasons.append('AUDIO_NOT_READY')
if hf.get('enabled') is not False or hf.get('microphone_open'):reasons.append('LISTENER_ACTIVE_OR_UNKNOWN')
if state.get('local_transcription',{}).get('service',{}).get('pending'):reasons.append('TRANSCRIPTION_PENDING')
if state.get('error'):reasons.append('UI_ERROR')
print(json.dumps({'ready_for_revalidation':not reasons,'wait_reasons':reasons,
 'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'runtime':str(runtime),'effective':effective,
 'phase':state.get('phase'),'audio_output_state':state.get('audio_output_state'),
 'monitor_enabled':hf.get('enabled'),'microphone_open':bool(hf.get('microphone_open')),
 'automatic_following':pan.get('automatic_following'),'pan_state':pan.get('state'),
 'pan_us':pan.get('pulse_us'),'motor_active':readback.get('active'),
 'follow_state':follow.get('state'),'follow_reason':follow.get('reason'),
 'duration_s':follow_config.get('duration_s'),'follow_mode':follow_config.get('mode'),
 'display':{key:display.get(key) for key in ('kind','fps','p95_ms','p99_ms','age_ms')},
 'actions_performed':[]}))
'''


def main():
    value = json.loads(ssh('python3 -B -', SCRIPT, timeout=20))
    value['checked_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    target = HERE / 'follow_wait_state.json'
    temp = target.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(target)
    print(json.dumps({key: item for key, item in value.items() if key != 'effective'}))


if __name__ == '__main__':
    main()
