"""Separate DPMS wake after failed visual trial, before physical HDMI comparison."""
import json
import os
from pathlib import Path
import subprocess
import time

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == 'c5f247b9-76b9-40a3-85ca-96578055eb5c'
p = Path('/sys/class/drm/card0-DP-1/dpms')
before = p.read_text().strip()
if before == 'Off':
    result = subprocess.run(['xset', 'dpms', 'force', 'on'], capture_output=True,
        text=True, timeout=8, env=dict(os.environ, DISPLAY=':0'))
    assert result.returncode == 0, result.stderr
    time.sleep(.5)
print(json.dumps(dict(scope='SEPARATE_NORMAL_WAKE_AFTER_USER_CONFIRMED_SOFTWARE_RECOVERY_FAILURE',
    before_dpms=before, after_dpms=p.read_text().strip(),
    dpms_wake_commands=1 if before == 'Off' else 0,
    timer_settings_changed=False, training_candidate_called=False)))
