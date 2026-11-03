"""One authorized recovery trial on the user-observed corrupted cold boot."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

boot = 'c5f247b9-76b9-40a3-85ca-96578055eb5c'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == boot
source = Path('/home/root/aura-post-power-20261022/helpers/474b8ce39ba29123/source.py')
assert hashlib.sha256(source.read_bytes()).hexdigest() == \
    '474b8ce39ba291233d23c25a2581d773b7b99809f9f1c37df5263789138d2221'
root = Path('/home/root/aura-display-sequence-20261024/one-shot') / (boot+'-474b8ce39ba29123')
assert not root.exists(), 'One-shot already used; refuse another attempt'
result = subprocess.run(['/usr/bin/python3', '-B', str(source), '--launch-once',
    '--boot', boot, '--camera-pid', '1309'], capture_output=True, text=True)
assert result.returncode == 0, result.stderr[-1000:]
launch = json.loads(result.stdout)
deadline = time.monotonic()+20
while time.monotonic() < deadline and not (root/'result.json').exists():
    time.sleep(.2)
report_path = root/('result.json' if (root/'result.json').exists() else 'progress.json')
print(json.dumps({'launch': launch, 'finished': (root/'result.json').exists(),
    'report': json.loads(report_path.read_text()) if report_path.exists() else None,
    'human_observed_corruption_before_trial': True,
    'human_visual_result_after_trial': 'PENDING',
    'whole_trial_includes_interface_capture_and_vblank_query': True}))
