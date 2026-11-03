"""Read existing sensor, display-clock and kernel evidence without reconfiguration."""
import json, re, subprocess, time
from pathlib import Path

def read(path):
    try:
        return path.read_text().strip()
    except (OSError, UnicodeError) as exc:
        return {'unavailable': str(exc)}

def sensors():
    values = {}
    for parent in [Path('/sys/bus/iio/devices'), Path('/sys/class/hwmon')]:
        for device in parent.glob('*'):
            if not (device/'name').exists():
                continue
            fields = {}
            for p in device.glob('*'):
                if re.fullmatch(r'(?:in_voltage\d*|in_current\d*|in_power\d*|in\d+|curr\d+|power\d+)_(?:input|raw|scale|label)', p.name):
                    fields[p.name] = read(p)
            if fields:
                values[str(device)] = {'name': read(device/'name'), 'values': fields}
    return values

v = {'boot_id': read(Path('/proc/sys/kernel/random/boot_id')),
     'files_modified': 0, 'display_commands_sent': 0, 'movement_commands_sent': 0}
v['sensor_samples'] = []
for i in range(5):
    if i:
        time.sleep(1)
    v['sensor_samples'].append({'uptime': read(Path('/proc/uptime')), 'sensors': sensors()})
v['drm_state'] = read(Path('/sys/kernel/debug/dri/0/state'))
clock = read(Path('/sys/kernel/debug/clk/clk_summary'))
v['display_clocks'] = [s for s in clock.splitlines() if re.search(r'dp_|dpsub|display|video', s, re.I)] if isinstance(clock, str) else clock
kernel = subprocess.check_output(['dmesg'], text=True, timeout=6)
v['display_events'] = [s for s in kernel.splitlines() if re.search(r'edid|zynqmp.*(?:dp|display)|drm.*(?:edid|fail|error|timeout)|dpdma|underflow|hpd|link.*(?:fail|error)|training', s, re.I)][-80:]
v['usb_errors'] = [s for s in kernel.splitlines() if re.search(r'usb.*(?:disconnect|reset|error|over.current|unable)', s, re.I)][-30:]
print(json.dumps(v), flush=True)
