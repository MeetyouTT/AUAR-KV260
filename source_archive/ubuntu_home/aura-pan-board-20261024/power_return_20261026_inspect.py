"""Read-only recovery inventory; never imports an actuator driver or opens MMIO."""
import hashlib
import json
import os
import platform
import subprocess
import urllib.request
from pathlib import Path

OLD_BOOT = '16a07283-9e14-45e6-816d-3bda4cf333a7'
ROOT = Path('/home/root/aura-pan-current-20261024/16a07283')
OPS = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')


def read(path, binary=False):
    try:
        return Path(path).read_bytes() if binary else Path(path).read_text().strip()
    except OSError:
        return None


def digest(path):
    data = read(path, True)
    return hashlib.sha256(data).hexdigest() if data is not None else None


def main():
    if platform.machine() != 'aarch64' or os.geteuid() != 0:
        raise RuntimeError('Board root execution required')
    boot = read('/proc/sys/kernel/random/boot_id')
    fw = read('/proc/device-tree/fpga-full/firmware-name', True)
    result = dict(status='POWER_RETURN_READ_ONLY_INVENTORY', boot_id=boot,
                  previous_boot_id=OLD_BOOT, changed_boot=boot != OLD_BOOT,
                  uptime=read('/proc/uptime'), firmware=fw.rstrip(b'\0').decode() if fw else None,
                  fdt_sha256=digest('/sys/firmware/fdt'),
                  fpga_state=read('/sys/class/fpga_manager/fpga0/state'),
                  machine=platform.machine(), mmio_opened=False, motor_commands_sent=0,
                  service_changes=0, mechanical_position_known=False)
    result['units'] = {}
    for unit in ('aura-camera-ui.service', 'aura-avatar-ui.service', 'aura-face-zone-editor.service'):
        r = subprocess.run(['systemctl', 'show', unit, '-p', 'MainPID', '-p', 'ActiveState',
                            '-p', 'SubState', '-p', 'Result', '-p', 'ExecMainStatus', '-p', 'NRestarts',
                            '-p', 'FragmentPath', '-p', 'DropInPaths'],
                           capture_output=True, text=True, timeout=4)
        result['units'][unit] = dict(returncode=r.returncode,
                                    properties=dict(line.split('=', 1) for line in r.stdout.splitlines() if '=' in line))
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for name, port, endpoint in (('camera', 8790, '/health'), ('ui', 8783, '/api/state')):
        try:
            with opener.open('http://127.0.0.1:%d%s' % (port, endpoint), timeout=3) as response:
                value = json.load(response)
            if name == 'camera':
                schedule = value.get('dpu_schedule') or {}
                identity = value.get('identity') or {}
                result[name] = dict(reachable=True, pid=value.get('pid'), identity_ready=identity.get('ready'),
                                    owner_fenced=schedule.get('owner_fenced'),
                                    primary_overruns=schedule.get('primary_period_overruns'),
                                    optional_overruns={k: v.get('overruns') for k, v in schedule.get('optional', {}).items()},
                                    health_keys=sorted(value), schedule_keys=sorted(schedule))
            else:
                m = value.get('manual_pan') or {}
                result[name] = dict(reachable=True, manual_state=m.get('state'), error=m.get('error'),
                                    message=m.get('message'), automatic_following=m.get('automatic_following'),
                                    readback=m.get('readback'), state_keys=sorted(value))
        except Exception as error:
            result[name] = dict(reachable=False, error_type=type(error).__name__)
    result['historical_release_sha256'] = {
        str(p): digest(p) for p in (OPS / 'continuous-v10r15/deployment-manifest.json',
                                   OPS / 'face-source-v17/deployment-manifest.json',
                                   ROOT / 'gui-manual-bound-v1/startup/config.json')}
    result['old_boot_context_sha256'] = digest(ROOT / 'context.json')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
