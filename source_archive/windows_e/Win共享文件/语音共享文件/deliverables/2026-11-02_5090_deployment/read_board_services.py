"""Bounded service, audio-device and camera-counter reads; no recording/control."""
import datetime
import http.client
import json
from pathlib import Path
import re
import subprocess
import time


def run(argv, timeout=6):
    try:
        value = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, timeout=timeout)
        return dict(exit_code=value.returncode, stdout=value.stdout[:16000], stderr=value.stderr[:1000])
    except (OSError, subprocess.TimeoutExpired) as error:
        return {'error': type(error).__name__}


def camera():
    connection = http.client.HTTPConnection('127.0.0.1', 8790, timeout=2)
    try:
        connection.request('GET', '/health')
        response = connection.getresponse()
        raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError('size_limit')
        data = json.loads(raw)
        keys = ('pid', 'board_boot_id', 'service_epoch', 'camera_epoch', 'capture_frames',
                'detected_frames', 'preview_frames', 'capture_age_ms', 'observation_age_ms',
                'camera_error', 'detector_error', 'preview_error', 'motion_command_emitted')
        return {key: data[key] for key in keys if key in data}
    except (OSError, ValueError, http.client.HTTPException) as error:
        return {'error': type(error).__name__}
    finally:
        connection.close()


journal = run(['journalctl', '-b', '-u', 'aura-avatar-ui.service', '-n', '80', '--no-pager', '-o', 'cat'])
audio_failures = []
for line in journal.get('stdout', '').splitlines():
    message = line
    if re.search(r'MCP01|audio hardware|sound card|ALSA|ModuleNotFoundError|ImportError', message, re.I):
        audio_failures.append(message[:350])

units = run(['systemctl', 'list-unit-files', '--type=service', '--no-pager'])
units['stdout'] = '\n'.join(line for line in units.get('stdout', '').splitlines()
                            if re.search(r'aura|xmutil|fpga|dfx|xlnx|timesync|chrony', line, re.I))
samples = []
for index in range(3):
    samples.append(dict(monotonic=time.monotonic(), metadata=camera()))
    if index != 2:
        time.sleep(1)
result = dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              board_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              audio_cards=run(['cat', '/proc/asound/cards']),
              capture_devices=run(['arecord', '-l']),
              playback_devices=run(['aplay', '-l']),
              units=units,
              effective_gui_service=run(['systemctl', 'show', 'aura-avatar-ui.service', '--no-pager',
                  '--property=ExecStart,WorkingDirectory,FragmentPath,DropInPaths,Result,ExecMainStatus']),
              fpga_manager_service=run(['systemctl', 'show', 'dfx-mgr.service', '--no-pager',
                  '--property=ExecStart,ActiveState,SubState']),
              gui_audio_failure_messages=audio_failures,
              time_service=run(['timedatectl', 'show', '-p', 'NTPSynchronized', '-p', 'NTP', '-p', 'Timezone']),
              camera_samples=samples, audio_opened=False, services_changed=False,
              database_opened=False, motion_requested=False)
print(json.dumps(result, ensure_ascii=False))
