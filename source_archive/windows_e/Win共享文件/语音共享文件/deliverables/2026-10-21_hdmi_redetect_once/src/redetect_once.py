"""Request one DRM connector re-probe and retain before/after evidence."""
import hashlib
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

BOOT = '5cd17bb7-30da-4a4f-bf18-8167508de1f4'
CONNECTOR = Path('/sys/class/drm/card0-DP-1')
DEBUG = Path('/sys/kernel/debug/dri/0/DP-1')
KNOWN_EDID = '727d3e1893df759c757c35232f9465b670a64d6de2011b586de48c6446e17c35'
FILES = [
    '/boot/uEnv.txt', '/boot/boot.scr', '/boot/system.dtb', '/etc/X11/xorg.conf',
    '/home/root/aura-speech-motion-20261021/922dab49a74f/startup/launcher.py',
    '/home/root/aura-speech-motion-20261021/922dab49a74f/startup/config.json',
]


def hashes():
    return {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in FILES}


def run(args):
    p = subprocess.run(args, env=dict(os.environ, DISPLAY=':0'),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, timeout=8)
    return dict(rc=p.returncode, text=p.stdout)


def units():
    return run(['systemctl', 'show', 'aura-avatar-ui.service', 'aura-camera-ui.service',
                'xserver-nodm.service', '-p', 'Id', '-p', 'MainPID',
                '-p', 'ActiveState', '-p', 'NRestarts'])


def state():
    raw = (CONNECTOR/'edid').read_bytes()
    valid = bool(len(raw) >= 128 and len(raw)%128 == 0
                 and raw[:8] == b'\x00\xff\xff\xff\xff\xff\xff\x00'
                 and len(raw) == 128*(1+raw[126])
                 and all(sum(raw[i:i+128])%256 == 0 for i in range(0,len(raw),128)))
    v = dict(uptime=Path('/proc/uptime').read_text().split()[0],
             edid_bytes=len(raw), edid_sha256=hashlib.sha256(raw).hexdigest(),
             edid_valid=valid, expected_edid=valid and hashlib.sha256(raw).hexdigest()==KNOWN_EDID)
    for name in ['status', 'enabled', 'dpms', 'modes']:
        v[name] = (CONNECTOR/name).read_text().strip()
    return v


def ui():
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open('http://127.0.0.1:8783/api/state', timeout=2) as r:
            s = json.load(r)
        return {k:s.get(k) for k in ['phase','ui_page','error','avatar_display']}
    except Exception as exc:
        return dict(error=type(exc).__name__+': '+str(exc))


def main():
    assert os.uname().machine == 'aarch64'
    assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == '0353445345333247805558c00401a100'
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
    assert Path('/sys/module/zynqmp_dpsub/parameters/power_on_delay_ms').read_text().strip() == '5000'
    assert (DEBUG/'force').read_text().strip() == 'unspecified'
    assert (DEBUG/'edid_override').read_bytes() == b''
    assert os.access(CONNECTOR/'status', os.W_OK)
    before = state()
    assert before['edid_bytes'] == 0 and before['status'] == 'connected'
    assert before['enabled'] == 'enabled' and before['dpms'] == 'On'
    before_units = units()
    assert before_units['rc'] == 0 and before_units['text'].count('ActiveState=active') == 3
    before_display = run(['xrandr', '--current'])
    assert before_display['rc'] == 0
    assert 'DP-1 connected primary 1024x600+0+0' in before_display['text']
    before_hashes = hashes()
    before_ui = ui()
    root = Path('/run/aura-hdmi-redetect-once-'+BOOT)
    root.mkdir(mode=0o700)  # Refuse a second attempt during this boot.
    result = dict(boot_id=BOOT, operation='single_connector_status_detect',
                  before=before, units_before=before_units, display_before=before_display,
                  ui_before=before_ui, hashes_before=before_hashes,
                  write_attempts=0, mode_set_commands_sent=0, reboots_sent=0,
                  movement_commands_sent=0, physical_panel_verified=False,
                  recovery_loop_installed=False, marker=str(root))
    (root/'before.json').write_text(json.dumps(result,indent=2)+'\n')
    # Keep the actual sysfs write in a child so the UART controller can report
    # a bounded timeout without waiting indefinitely for a stuck kernel write.
    code = ('import os,json,time\n'
            'started=time.monotonic()\n'
            'fd=os.open("/sys/class/drm/card0-DP-1/status",os.O_WRONLY)\n'
            'try:n=os.write(fd,b"detect\\n")\n'
            'finally:os.close(fd)\n'
            'print(json.dumps({"bytes_written":n,"elapsed_seconds":time.monotonic()-started}),flush=True)\n')
    started = time.monotonic()
    result['write_attempts'] = 1
    with (root/'writer.out').open('xb') as stream:
        child = subprocess.Popen(['/usr/bin/python3','-c',code], stdout=stream,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        while child.poll() is None and time.monotonic()-started < 12:
            time.sleep(0.1)
        if child.poll() is None:
            child.kill()
            result.update(writer_timeout=True, writer_pid=child.pid,
                          decision='stop_on_timeout_no_further_drm_reads')
        else:
            result.update(writer_timeout=False, writer_exit_code=child.returncode,
                          writer_output=(root/'writer.out').read_text(errors='replace'))
    result['operation_elapsed_seconds'] = round(time.monotonic()-started,3)
    if not result['writer_timeout']:
        result['after'] = state()
        time.sleep(3)
        result['after_3s'] = state()
        result['units_after'] = units()
        result['display_after'] = run(['xrandr','--current'])
        result['ui_after'] = ui()
        result['hashes_after'] = hashes()
        result['protected_files_unchanged'] = result['hashes_after'] == before_hashes
        result['units_unchanged'] = result['units_after'] == before_units
        result['force_after'] = (DEBUG/'force').read_text().strip()
        result['override_bytes_after'] = len((DEBUG/'edid_override').read_bytes())
        if result['writer_exit_code'] != 0:
            result['decision'] = 'stop_after_writer_error'
        elif result['after']['expected_edid'] and result['after_3s']['expected_edid']:
            result['decision'] = 'edid_recovered_physical_feedback_required'
        else:
            result['decision'] = 'edid_not_recovered_no_retry'
    (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
