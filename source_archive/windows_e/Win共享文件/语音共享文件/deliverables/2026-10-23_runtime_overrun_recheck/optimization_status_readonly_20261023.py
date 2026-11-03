import hashlib
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(port, route):
    with opener.open('http://127.0.0.1:%d%s' % (port, route), timeout=3) as response:
        return json.load(response)


def cpu():
    values = [int(value) for value in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    return sum(values), values[3] + values[4]


start_time = time.monotonic()
first_cpu = cpu()
before = get(8790, '/health')
time.sleep(3)
after = get(8790, '/health')
last_cpu = cpu()
duration = time.monotonic() - start_time
pid = after['pid']
start_ticks = int((Path('/proc') / str(pid) / 'stat').read_text().split(') ')[1].split()[19])
process_start_s = start_ticks / os.sysconf('SC_CLK_TCK')
uptime_s = float(Path('/proc/uptime').read_text().split()[0])
schedule = after.get('dpu_schedule') or {}
diagnostics = schedule.get('optional_diagnostics') or {}
events = diagnostics.get('fault_events') or []
faults = [event for event in events if event.get('hardcap_exceeded') or event.get('guard_exceeded')]
identity = after.get('identity') or {}
face = identity.get('face_targets') or {}
unit = Path('/etc/systemd/system/aura-camera-ui.service')
ui = get(8783, '/api/state')
usb = subprocess.run(['journalctl', '-k', '-b', '-n', '5000', '-o', 'json', '--no-pager'], stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, timeout=8)
usb_info = {'query_returncode': usb.returncode, 'kernel_tail_cap': 5000}
if usb.returncode == 0:
    rows = [json.loads(line) for line in usb.stdout.splitlines() if line.startswith(b'{')]
    all_times = [int(row['__MONOTONIC_TIMESTAMP']) / 1e6 for row in rows]
    times = [int(row['__MONOTONIC_TIMESTAMP']) / 1e6 for row in rows
             if "WARN: HC couldn't access mem fast enough" in row.get('MESSAGE', '')]
    earliest_s = min(all_times) if all_times else None
    usb_info.update(kernel_tail_records=len(rows), earliest_kernel_monotonic_s=earliest_s,
                    covers_process_start=earliest_s is not None and earliest_s <= process_start_s,
                    matching_since_process_start=sum(value >= process_start_s for value in times))
    if faults:
        fault_s = faults[-1]['optional_end_mono_ns'] / 1e9
        usb_info['matching_within_fault_plus_minus_60s'] = sum(abs(value - fault_s) <= 60 for value in times)
        usb_info['covers_fault_plus_minus_60s'] = earliest_s is not None and earliest_s <= fault_s - 60 and uptime_s >= fault_s + 60
else:
    usb_info['query_error'] = usb.stderr.decode(errors='replace')[-300:]

delta_total = last_cpu[0] - first_cpu[0]
out = {'read_only': True,
       'boot': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
       'camera_pid': pid, 'same_pid': pid == before['pid'],
       'camera_process_age_s': uptime_s - process_start_s,
       'unit_sha256': hashlib.sha256(unit.read_bytes()).hexdigest(),
       'detector': after.get('detector'), 'camera_error': after.get('camera_error'),
       'detector_error': after.get('detector_error'), 'capture_hz': after.get('capture_hz'),
       'detection_hz': after.get('detection_hz'), 'detected_frame_delta': after['detected_frames'] - before['detected_frames'],
       'cpu_sample_duration_s': duration,
       'cpu_percent_of_board': 100 * (1 - (last_cpu[1] - first_cpu[1]) / delta_total),
       'formal_identity_backend': identity.get('backend'), 'face_backend': face.get('backend'),
       'face_last_inference_ms': face.get('last_inference_ms'),
       'face_source_age_ms': face.get('source_age_ms'),
       'freshness_counters': (face.get('freshness_metrics') or {}).get('counters'),
       'yunet_schedule': (schedule.get('optional') or {}).get('yunet'),
       'primary_period_overruns': schedule.get('primary_period_overruns'),
       'fault_events': faults, 'usb_warning_query': usb_info,
       'audio_state': {key: ui.get(key) for key in ('phase', 'playing', 'paused', 'audio_output_state')}}
for event in faults:
    event['seconds_after_camera_start'] = event['optional_end_mono_ns'] / 1e9 - process_start_s
print(json.dumps(out))
