"""Stage a reversible, single-parameter DP wake delay for the next boot."""
import hashlib
import json
import os
import struct
import subprocess
import zlib
from pathlib import Path

EXPECTED_BOOT = 'fc221b0d-b9f4-40a2-b509-6c53478a89d0'
BASE_ARGS = 'earlycon console=ttyPS1,115200 clk_ignore_unused root=/dev/ram0 rw init_fatal_sh=1 cma=1536M'
PARAMETER = 'zynqmp_dpsub.power_on_delay_ms=5000'
BACKUP = '/boot/aura-hdmi-delay5-20261021'
PAYLOAD = ('bootargs=' + BASE_ARGS + ' ' + PARAMETER + '\n'
           'uenvcmd=echo AURA DP wake delay configured: 5000 ms\n').encode('ascii')
EXPECTED_HASHES = {
    '/boot/boot.scr': '9ada4d88212468c12d2710b0fae35df42c4c72134bafa82b2ae5aca82570a7f1',
    '/etc/X11/xorg.conf': '164afc02188bb108230acd9a6e54b30ff145d131c6c070579fd501751c20e06e',
    '/home/root/aura-speech-motion-20261021/922dab49a74f/startup/launcher.py': 'cd1680220b60f6120db1bc847ca59cfd445796ff37e48a3ba93efca65eddfd98',
    '/home/root/aura-speech-motion-20261021/922dab49a74f/startup/config.json': '1815ddb8c1eae71b511a46df0e28baafbaf19fdc877745b587079732b24e36c7',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


ROLLBACK = '''"""Disable only the exact delay configuration installed with this backup."""
import hashlib,json,os
from pathlib import Path
def disable(root):
    backup=root/'aura-hdmi-delay5-20261021'
    meta=json.loads((backup/'before.json').read_text())
    target=root/'uEnv.txt'
    if target.is_symlink():raise RuntimeError('Refusing a symbolic link')
    if not target.exists():return 'already_absent'
    if hashlib.sha256(target.read_bytes()).hexdigest()!=meta['installed_uenv_sha256']:
        raise RuntimeError('uEnv.txt changed since install; refusing to remove it')
    saved=backup/'uEnv.disabled'
    if saved.exists():raise RuntimeError('Rollback destination already exists')
    target.rename(saved)
    os.sync()
    return 'disabled_for_next_boot'
if __name__=='__main__':
    root=Path(__file__).resolve().parent.parent
    print(json.dumps({'result':disable(root),'current_runtime_parameter_unchanged':True}))
'''


def units():
    return subprocess.check_output([
        'systemctl', 'show', 'aura-avatar-ui.service', 'aura-camera-ui.service',
        'xserver-nodm.service', '-p', 'Id', '-p', 'MainPID', '-p', 'ActiveState',
        '-p', 'NRestarts'], text=True, timeout=5)


def main():
    assert os.uname().machine == 'aarch64'
    assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == '0353445345333247805558c00401a100'
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    assert boot == EXPECTED_BOOT, 'Board boot changed; re-read before installing'
    assert Path('/proc/cmdline').read_text().strip() == BASE_ARGS
    assert Path('/proc/device-tree/chosen/bootargs').read_bytes().rstrip(b'\0').decode() == BASE_ARGS
    parameter_path = Path('/sys/module/zynqmp_dpsub/parameters/power_on_delay_ms')
    assert parameter_path.read_text().strip() == '4'
    mounts = [line.split() for line in Path('/proc/mounts').read_text().splitlines()]
    assert any(m[0:3] == ['/dev/mmcblk1p1', '/boot', 'vfat'] and 'rw' in m[3].split(',') for m in mounts)
    target = Path('/boot/uEnv.txt')
    backup = Path(BACKUP)
    assert not target.exists() and not target.is_symlink(), 'Preserve existing uEnv.txt'
    assert not backup.exists() and not backup.is_symlink(), 'Preserve existing backup'
    originals = {p:Path(p).read_bytes() for p in EXPECTED_HASHES}
    assert {p:sha(b) for p,b in originals.items()} == EXPECTED_HASHES
    script = originals['/boot/boot.scr']
    header = bytearray(script[:64]); fields = struct.unpack('>7I4B32s', header)
    header[4:8] = b'\0'*4
    assert fields[0] == 0x27051956 and len(script) == 64 + fields[3]
    assert zlib.crc32(header)&0xffffffff == fields[1]
    assert zlib.crc32(script[64:])&0xffffffff == fields[6]
    assert b'env import -t 0x00200000 $filesize' in script and b'run uenvcmd' in script
    before_units = units()
    assert before_units.count('ActiveState=active') == 3
    dtb = Path('/boot/system.dtb').read_bytes()
    meta = dict(boot_id=boot, original_uenv_present=False, original_cmdline=BASE_ARGS,
                installed_uenv_sha256=sha(PAYLOAD), protected_hashes=EXPECTED_HASHES,
                original_dtb_sha256=sha(dtb), units=before_units)
    backup.mkdir()
    for name,data in [('before.json',(json.dumps(meta,indent=2)+'\n').encode()),
                      ('boot.scr.before',script), ('system.dtb.before',dtb),
                      ('uEnv.candidate',PAYLOAD), ('rollback.py',ROLLBACK.encode())]:
        with (backup/name).open('xb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
    os.sync()
    temporary = Path('/boot/uEnv.aura-delay5.pending')
    with temporary.open('xb') as f:
        f.write(PAYLOAD); f.flush(); os.fsync(f.fileno())
    assert temporary.read_bytes() == PAYLOAD
    assert not target.exists() and not target.is_symlink()
    temporary.rename(target)
    os.sync()
    assert target.read_bytes() == PAYLOAD
    assert {p:sha(Path(p).read_bytes()) for p in EXPECTED_HASHES} == EXPECTED_HASHES
    assert sha(Path('/boot/system.dtb').read_bytes()) == sha(dtb)
    after_units = units()
    result = dict(boot_id=boot, installed=True, uenv_sha256=sha(PAYLOAD),
                  uenv_text=PAYLOAD.decode(), backup=str(backup),
                  runtime_delay_ms=parameter_path.read_text().strip(),
                  runtime_cmdline=Path('/proc/cmdline').read_text().strip(),
                  units_before=before_units, units_after=after_units,
                  units_unchanged=before_units == after_units,
                  protected_files_unchanged=True, current_display_commands_sent=0,
                  reboots_sent=0, movement_commands_sent=0,
                  effective_after_next_boot=True, physical_fix_verified=False)
    (backup/'install-result.json').write_text(json.dumps(result,indent=2)+'\n')
    os.sync()
    print(json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
