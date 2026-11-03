"""Overlay only echo confirmation on the currently effective UI runtime."""
import base64
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

base = json.loads(ssh('python3 -B -', r'''
import base64,json,re,subprocess
from pathlib import Path
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
path=Path(re.findall(r'--config (\S+)',unit)[-1])
effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
assert str(path) in effective
cfg=json.loads(path.read_text());root=Path(cfg['runtime'])
names=['aura/tools/barge_in_capture.py','aura/tools/barge_in_recording.py']
print(json.dumps({'ui_unit':unit,'runtime':str(root),'config_path':str(path),
 'startup_config':cfg,'baseline_files':{n:base64.b64encode((root/n).read_bytes()).decode() for n in names}}))
''', timeout=15))
(HERE / 'board_baseline.json').write_text(json.dumps(base, indent=2), encoding='utf-8')
names = ['aura/tools/barge_in_capture.py', 'aura/tools/barge_in_recording.py',
         'aura/board/runtime/audio/barge_verify.py', 'aura/tests/framework/test_barge_verification.py']
payload = {name: base64.b64encode((ROOT / name).read_bytes()).decode() for name in names}
# Reuse the verified copy-on-overlay, source-pin, test and preflight workflow.
template = (ROOT / 'deliverables/2026-10-20_listening_timing/prepare.py').read_text(encoding='utf-8')
remote = template.split("remote=r'''", 1)[1].split("'''.replace('BASE'", 1)[0]
remote = remote.replace('aura-listening-timing-20261020', 'aura-echo-verify-20261021')
remote = remote.replace("modules=['test_listening_timing'", "modules=['test_barge_verification','test_listening_timing'", 1)
remote = remote.replace('BASE', repr(base), 1).replace('PAYLOAD', repr(payload), 1)
result = json.loads(ssh('python3 -B -', remote, timeout=250))
for name in ('tests_log', 'preflight_log'):
    (HERE / (name + '.log')).write_text(result.pop(name), encoding='utf-8')
(HERE / 'candidate.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({key: result[key] for key in ('runtime', 'tests_passed', 'preflight_passed')}), flush=True)
print((HERE / 'tests_log.log').read_text(encoding='utf-8'), flush=True)
assert result['tests_passed'] and result['preflight_passed']
