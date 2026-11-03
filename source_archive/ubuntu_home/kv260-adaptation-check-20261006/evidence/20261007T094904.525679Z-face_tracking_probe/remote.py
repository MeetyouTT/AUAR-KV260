"""Read bounded live tracking samples; do not touch camera, display or motion."""
import json
import time
from pathlib import Path

current = json.loads(Path('/home/root/aura-realtime-vision-20261007/current.json').read_text())
root = Path(current['run_root'])
samples = []
for _ in range(16):
    state = json.loads((root/'status.json').read_text())
    samples.append(state)
    time.sleep(1)
events = (root/'events.jsonl').read_text()[-12000:]
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
passed = (
    boot == samples[-1]['boot_id']
    and samples[-1]['pid'] == current['pid']
    and all(samples[-1][key] > samples[0][key] for key in
            ['capture_frames', 'detected_frames', 'display_frames', 'rendered_frames'])
    and all(not item['error'] and not item['stopped'] for item in samples)
)
print(json.dumps({'passed': passed, 'boot_id': boot, 'pid': current['pid'],
                  'run_root': str(root), 'samples': samples, 'events_tail': events,
                  'probe_motion_command_emitted': False, 'probe_fpga_modified': False}))
assert passed
