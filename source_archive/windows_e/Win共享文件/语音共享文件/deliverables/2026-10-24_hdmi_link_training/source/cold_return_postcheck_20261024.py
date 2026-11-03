"""Read-only post-trial availability, cleanup and protected identity checks."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request

boot = 'c5f247b9-76b9-40a3-85ca-96578055eb5c'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == boot
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health', timeout=3) as stream:
    h = json.load(stream)
s = h['dpu_schedule']; i = h['identity']; f = i['face_targets']
root = Path('/home/root/aura-display-sequence-20261024/one-shot')/(boot+'-474b8ce39ba29123')
report = json.loads((root/'result.json').read_text())
meta = json.loads(Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/meta.json').read_text())
config = json.loads(Path(meta['candidate_config']).read_text())
identity_path = Path(config['identity']['config']); identity = json.loads(identity_path.read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
cfg_sha = sha(identity_path); db_sha = sha(identity['database'])
unit = 'aura-one-train-474b8ce39ba29123-c5f247b9.service'
text = subprocess.check_output(['systemctl', 'show', unit, '-p', 'ActiveState',
    '-p', 'SubState', '-p', 'Result', '-p', 'ExecMainStatus', '-p', 'MainPID'], text=True)
messages = subprocess.check_output(['dmesg'], text=True)
start = report['trigger_result']['started_mono_ns']/1e9
new_errors = []
for row in messages.splitlines():
    match = re.match(r'\[\s*(\d+\.\d+)\]', row)
    if match and float(match[1]) >= start and re.search(
            r'WARNING:|BUG:|Oops:|Call trace:|failed to train|training failed', row, re.I):
        new_errors.append(row)
p = Path('/sys/class/drm/card0-DP-1')
print(json.dumps(dict(boot=boot, mono_ns=time.monotonic_ns(),
    camera_pid=h['pid'], same_camera_pid=h['pid']==report['before_camera']['pid'],
    frames=h['detected_frames'], yolo_hz=h['detection_hz'],
    native_critical=s.get('native_critical'), owner_fenced=s['owner_fenced'],
    camera_error=bool(h.get('camera_error') or h.get('detector_error')),
    primary_overruns=s['primary_period_overruns'],
    optional_overruns={k:v['overruns'] for k,v in s['optional'].items()},
    face_worker_alive=f['worker_alive'], sface_ready=i['feature_inference']['ready'],
    sface_completed=i['feature_inference']['completed'],
    face_gaps=f['freshness_metrics']['counters']['observed_gap_intervals'],
    display={k:(p/k).read_text().strip() for k in ['status','enabled','dpms']},
    module_removed=not Path('/sys/module/aura_dp_retrain_candidate').exists(),
    owned_trace_removed=not (Path('/sys/kernel/tracing/instances')/('aura_once_474b8ce39ba29123_'+boot[:8])).exists(),
    maintenance_unit=dict(row.split('=',1) for row in text.splitlines() if '=' in row),
    identity_config_sha256=cfg_sha, database_sha256=db_sha,
    identity_config_unchanged=cfg_sha=='398ece6a4d5d81076c9a4f9f40a43e97cedd469e0b47e3a835e589a2255ca6e3',
    database_unchanged=db_sha=='ee22b97dbaa6f29f5b76c18565acc4f597cd61c6090f1946b993d2a29ab8101a',
    new_kernel_error_lines_matching_filter=len(new_errors),
    kernel_error_filter='WARNING/BUG/Oops/Call trace/failed to train/training failed after trigger start',
    human_visual_result='PENDING')))
