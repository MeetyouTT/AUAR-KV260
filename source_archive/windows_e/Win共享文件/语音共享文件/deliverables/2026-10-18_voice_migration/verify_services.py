"""Verify moved services with deployed board client; no new recording/playback."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
DIALOGUE=ROOT/'deliverables/2026-10-18_board_dialogue'
sys.path.insert(0,str(DIALOGUE))
from board_ssh import ssh

inventory=(DIALOGUE/'board_inventory.py').read_text(encoding='utf-8')
raw=ssh('python3 -',inventory,timeout=40)
after=json.loads(raw)
(HERE/'board_after_switch.json').write_text(raw,encoding='utf-8')
before=json.loads((HERE/'board_before_switch.json').read_text(encoding='utf-8-sig'))
for name in ('host_asr','host_voice'):
    assert after[name]['status']==200 and after[name]['value']['ready'],name
assert after['host_voice']['value']['num_step']==16
assert before['boot_id']==after['boot_id'],'Board rebooted'
assert before['ui_unit']==after['ui_unit'],'UI unit changed'
assert after['ui']['value']['phase']=='IDLE'
assert not after['host_voice']['value']['busy'],'Host busy'
probe=(DIALOGUE/'probe_board_client.py').read_text(encoding='utf-8')
old="(HERE/'board_client_probe.json').write_text"
new="(ROOT/'deliverables/2026-10-18_voice_migration/board_client_probe.json').write_text"
assert probe.count(old)==1
exec(compile(probe.replace(old,new),str(DIALOGUE/'probe_board_client.py'),'exec'),{'__name__':'__main__'})
result=json.loads((HERE/'board_client_probe.json').read_text(encoding='utf-8'))
assert result['status']=='PASS_BOARD_CLIENT_ACTUAL_MODELS'
assert result['historical_recording'] and not result['physical_playback']
raw=ssh('python3 -',inventory,timeout=40)
(HERE/'board_after_probe.json').write_text(raw,encoding='utf-8')
print('PASS_MIGRATED_SERVICES_FROM_BOARD_AND_CLIENT')
