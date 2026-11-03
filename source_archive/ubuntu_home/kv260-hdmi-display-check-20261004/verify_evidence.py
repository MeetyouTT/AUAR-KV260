#!/usr/bin/env python3
"""Review captured UART display evidence without accessing the board."""
import base64
import datetime
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
UART = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004')
PHASES = [
    UART / 'evidence/20261004T122419.533161Z-39-display-readonly-inventory',
    UART / 'evidence/20261004T122614.821640Z-40-display-xorg-readonly',
    UART / 'evidence/20261004T122750.224677Z-41-display-wake-native-mode',
]
checks = []
files = {}


def check(name, condition):
    checks.append({'name': name, 'passed': bool(condition)})
    if not condition:
        raise RuntimeError(name)


def record(path):
    data = path.read_bytes()
    files[str(path)] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    return data


def captured(phase, name):
    return json.loads((PHASES[phase] / (name + '.output')).read_text())


for phase in PHASES:
    status = json.loads(record(phase / 'status.json'))
    check(phase.name + ': complete', status['complete'])
    check(phase.name + ': root shell confirmed', status['root_shell_confirmed'])
    check(phase.name + ': console echo restored', status['console_echo_restored'])
    manifest = record(phase / 'manifest.json')
    check(phase.name + ': captured manifest hash',
          hashlib.sha256(manifest).hexdigest() == status['manifest_sha256'])
    check(phase.name + ': current manifest unchanged',
          record(Path(status['manifest'])) == manifest)
    rows = json.loads(manifest)
    check(phase.name + ': every entry accounted for',
          [r['id'] for r in rows] == [r['id'] for r in status['results']])
    for result in status['results']:
        check(phase.name + ': ' + result['id'] + ' returned zero', result['exit_code'] == 0)
        data = record(phase / (result['id'] + '.output'))
        check(phase.name + ': ' + result['id'] + ' output length and hash',
              len(data) == result['bytes'] and
              hashlib.sha256(data).hexdigest() == result['output_sha256'])
    record(phase / 'serial.raw')

identity = captured(0, 'board-identity')
check('expected SD card and kernel',
      identity['sd_cid'] == '0353445345333247805558c00401a100' and
      identity['kernel'] == '5.15.36-xilinx-v2022.2')
check('current boot identity', identity['boot_id'] == 'b39598d6-1118-4ef3-af52-36f0c1a4d396')
initial = captured(0, 'drm-connectors-and-edid')['connectors']['card0-DP-1']
check('initial connected but output disabled',
      initial['status'] == 'connected' and initial['enabled'] == 'disabled' and initial['dpms'] == 'Off')
check('initial EDID cache empty', initial['edid']['bytes'] == 0)
queries = captured(1, 'xrandr-xset-modetest-query')
check('Xorg mode query succeeds and reports preferred 1024x600',
      queries[0]['rc'] == 0 and re.search(r'1024x600.*preferred', queries[0]['stdout']))
check('initial power saving state off at 600 seconds',
      queries[1]['rc'] == 0 and 'Monitor is Off' in queries[1]['stdout'] and
      'Standby: 600    Suspend: 600    Off: 600' in queries[1]['stdout'])
check('preserved unsuccessful modetest driver-name attempt',
      queries[2]['rc'] == 255 and "failed to open device 'xlnx'" in queries[2]['stderr'])
after_probe = captured(1, 'display-live-device-tree')
check('EDID readable after Xorg probe', after_probe['edid_bytes_after_probe'] == 128)
change = captured(2, 'wake-and-native-mode')
check('wake and native mode change succeeds', change['runtime_mode_and_wake_passed'])
check('runtime commands only, no persistent file change', not change['persistent_configuration_changed'])
check('all six captured runtime operations returned zero',
      len(change['commands']) == 6 and all(c['rc'] == 0 for c in change['commands']))
check('Xorg confirms current and preferred native mode',
      'DP-1 connected primary 1024x600+0+0' in change['commands'][4]['stdout'] and
      '*current +preferred' in change['commands'][4]['stdout'])
check('Xorg confirms monitor on', 'Monitor is On' in change['commands'][5]['stdout'])
post = captured(2, 'native-output-kernel-state')
state = post['files']
check('sysfs independently confirms connected, enabled, on',
      all(state['/sys/class/drm/card0-DP-1/' + k].strip() == v
          for k, v in [('status', 'connected'), ('enabled', 'enabled'), ('dpms', 'On')]))
drm = state['/sys/kernel/debug/dri/0/state']
check('DRM scanout enabled and active with native framebuffer',
      '\tenable=1\n' in drm and '\tactive=1\n' in drm and
      '\t\tsize=1024x600\n' in drm and 'allocated by = Xorg' in drm)
edid = base64.b64decode(post['edid']['base64'], validate=True)
check('EDID size, signature, hash and checksum',
      len(edid) == 128 and edid[:8] == b'\x00\xff\xff\xff\xff\xff\xff\x00' and
      hashlib.sha256(edid).hexdigest() == post['edid']['sha256'] and sum(edid) % 256 == 0)
dtd = edid[54:72]
pixel_clock = int.from_bytes(dtd[:2], 'little') * 10000
ha = dtd[2] + ((dtd[4] >> 4) << 8)
hb = dtd[3] + ((dtd[4] & 15) << 8)
va = dtd[5] + ((dtd[7] >> 4) << 8)
vb = dtd[6] + ((dtd[7] & 15) << 8)
refresh = pixel_clock / (ha + hb) / (va + vb)
check('EDID preferred timing independently decoded',
      (ha, va, pixel_clock) == (1024, 600, 49000000) and abs(refresh - 59.85) < 0.01)
check('modetest using actual display bus ID succeeds', post['commands'][0]['rc'] == 0)
check('modetest confirms native scanout',
      re.search(r'41\s+47\s+\(0,0\)\s+\(1024x600\)', post['commands'][0]['stdout']))
check('Xorg reports good link status', 'link-status: Good' in change['commands'][4]['stdout'])
check('manager and display service remain active',
      post['commands'][1]['rc'] == 0 and
      post['commands'][1]['stdout'].count('ActiveState=active') == 2 and
      'MainPID=1018' in post['commands'][1]['stdout'] and 'MainPID=994' in post['commands'][1]['stdout'])
pre_log = (PHASES[0] / 'current-kernel-log.output').read_text()
post_log = post['commands'][2]['stdout']
check('post-mode kernel log command succeeds', post['commands'][2]['rc'] == 0)
check('kernel log retains earlier records', post_log.startswith(pre_log))
delta = post_log[len(pre_log):]
check('no new recorded link training failure or fatal kernel trace',
      re.search(r'failed to train|\bOops\b|Kernel panic|Call trace:|clock.*failed', delta, re.I) is None)
check('two boot display clock permission warnings still present',
      len(re.findall(r'ret\s*=\s*-13', post_log)) == 2)
xorg = captured(1, 'xorg-process-and-configuration')['files']['/var/log/Xorg.0.log']
check('GLX module absence preserved as a limitation',
      'Failed to load module "glx"' in xorg and 'Soft EXA mode' in xorg)
record(Path(__file__).resolve())
result = {
    'reviewed_at_host_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'checks': checks,
    'check_count': len(checks),
    'all_passed': all(c['passed'] for c in checks),
    'board_identity': identity,
    'output_mode': {'width': ha, 'height': va, 'refresh_hz': refresh,
                    'pixel_clock_hz': pixel_clock, 'link_status': 'Good'},
    'output_enabled_verified': True,
    'physical_picture_verified': False,
    'user_screen_observation': None,
    'persistent_display_configuration_changed': False,
    'screen_power_saving_seconds': 600,
    'boot_clock_warnings_fixed': False,
    'full_UI_or_3D_rendering_verified': False,
    'DPU_inference_rerun_in_this_task': False,
    'evidence_files': files,
}
path = ROOT / 'EVIDENCE_REVIEW.json'
with path.open('x') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'review': str(path), 'checks': len(checks), 'all_passed': result['all_passed'],
                  'evidence_files': len(files), 'physical_picture_verified': False}, ensure_ascii=False))
