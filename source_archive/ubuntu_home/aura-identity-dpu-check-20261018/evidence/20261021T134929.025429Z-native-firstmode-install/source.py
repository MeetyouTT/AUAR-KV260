"""Install or withdraw only the native Xorg mode and early-fbdev boot setting."""
import hashlib
import json
import os
import stat
import sys
import uuid
from pathlib import Path

BACKUP = '/boot/aura-native-firstmode-20261021'
CID = '0353445345333247805558c00401a100'
BOOT = 'bec99c5a-5292-4a3e-b180-c52187d6c47b'
OLD_XORG = '164afc02188bb108230acd9a6e54b30ff145d131c6c070579fd501751c20e06e'
OLD_UENV = '05cd73695dc8797899ee32a02ba5081403f02d5b28b8b89b3b71ffe503279ffe'
NATIVE_XORG = 'Section "InputDevice"\n\tIdentifier\t"System Mouse"\n\tDriver\t\t"mouse"\n\tOption\t\t"Device" "/dev/input/mouse0"\nEndSection\n\nSection "InputDevice"\n\tIdentifier\t"System Keyboard"\n\tDriver\t\t"kbd"\n\tOption\t\t"Device" "/dev/input/event0"\nEndSection\n\nSection "Device"\n        Identifier      "ZynqMP"\n        Driver          "armsoc"\n        Option          "BusId"                 "fd4a0000.display"\n        Option          "DRI2"                  "true"\n        Option          "DRI2_PAGE_FLIP"        "false"\n        Option          "DRI2_WAIT_VSYNC"       "true"\n        Option          "SWcursorLCD"           "false"\n        Option          "DEBUG"                 "false"\n        Option          "Monitor-DP-1"          "AURA-HDMI"\nEndSection\n\n# Exact 49 MHz timing read from this panel\'s verified EDID.\n# The narrow sync ranges enclose 37.34756 kHz / 59.85186 Hz.\nSection "Monitor"\n        Identifier      "AURA-HDMI"\n        HorizSync       37.34-37.36\n        VertRefresh     59.84-59.86\n        Modeline        "1024x600" 49.000 1024 1072 1168 1312 600 603 613 624 -HSync -VSync\n        Option          "PreferredMode" "1024x600"\n        Option          "Primary" "true"\nEndSection\n\nSection "Screen"\n        Identifier      "DefaultScreen"\n        Device          "ZynqMP"\n        Monitor         "AURA-HDMI"\n        DefaultDepth    16\n        SubSection "Display"\n                Depth   16\n                Modes   "1024x600"\n        EndSubSection\nEndSection\n'
PROTECTED = {
    '/boot/Image':'b02771b1c6ceca7f07b56a97ab36d79d2f17652c58f9c119ddd1d2ea0e554e71',
    '/boot/boot.scr':'9ada4d88212468c12d2710b0fae35df42c4c72134bafa82b2ae5aca82570a7f1',
    '/boot/system.dtb':'7b0ec669233e0a9b18f2e853dfe7610c58c18ed33e07fe7e682290bc574c7d32',
    '/home/root/aura-audio-frontend-20261021/candidate-fe6f5c7b1b56/startup/launcher.py':'cd1680220b60f6120db1bc847ca59cfd445796ff37e48a3ba93efca65eddfd98',
    '/home/root/aura-audio-frontend-20261021/candidate-fe6f5c7b1b56/startup/config.json':'3721a1f6101a4e14f88cab7f66e4430886206a55b21fafa33c56acf56c9395a0',
}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def atomic_write(path, data, mode=0o644):
    temporary = path.with_name('.'+path.name+'.aura-native-'+uuid.uuid4().hex)
    try:
        with temporary.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
        descriptor = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()

def rollback(root=Path('/')):
    backup = root/BACKUP.lstrip('/')
    manifest = json.loads((backup/'manifest.json').read_text())
    entries = manifest['targets']
    # Check every file first; never overwrite a later change.
    for entry in entries:
        target = root/entry['path'].lstrip('/')
        before = (backup/entry['before_file']).read_bytes()
        assert digest(before) == entry['before_sha256']
        assert not target.is_symlink()
        assert digest(target.read_bytes()) in [entry['before_sha256'], entry['after_sha256']]
    for entry in reversed(entries):
        target = root/entry['path'].lstrip('/')
        if digest(target.read_bytes()) != entry['before_sha256']:
            atomic_write(target, (backup/entry['before_file']).read_bytes(), entry['mode'])
        assert digest(target.read_bytes()) == entry['before_sha256']
    return {'status':'CONFIGURATION_ROLLED_BACK_NEXT_START', 'targets':len(entries)}

def install(root=Path('/'), protected=PROTECTED, writer=atomic_write):
    xorg = root/'etc/X11/xorg.conf'
    uenv = root/'boot/uEnv.txt'
    assert not xorg.is_symlink() and not uenv.is_symlink()
    old_xorg, old_uenv = xorg.read_bytes(), uenv.read_bytes()
    assert digest(old_xorg) == OLD_XORG, 'Xorg changed since inventory'
    assert digest(old_uenv) == OLD_UENV, 'uEnv changed since inventory'
    assert '__XORG_PLACEHOLDER__' not in NATIVE_XORG
    assert b'drm_kms_helper.fbdev_emulation' not in old_uenv
    lines = old_uenv.decode().splitlines(keepends=True)
    assert sum(line.startswith('bootargs=') for line in lines) == 1
    new_uenv = ''.join(line.rstrip('\r\n')+' drm_kms_helper.fbdev_emulation=0\n'
                       if line.startswith('bootargs=') else line for line in lines).encode()
    new_xorg = NATIVE_XORG.encode()
    for name, expected in protected.items():
        assert digest((root/name.lstrip('/')).read_bytes()) == expected, name
    backup = root/BACKUP.lstrip('/')
    backup.mkdir(mode=0o755, exist_ok=False)
    targets = []
    for name, target, before, after in [('xorg',xorg,old_xorg,new_xorg), ('uenv',uenv,old_uenv,new_uenv)]:
        (backup/(name+'.before')).write_bytes(before)
        (backup/(name+'.installed')).write_bytes(after)
        targets.append({'path':'/'+str(target.relative_to(root)), 'before_file':name+'.before',
                        'before_sha256':digest(before), 'after_sha256':digest(after),
                        'mode':stat.S_IMODE(target.stat().st_mode)})
    manifest = {'boot_id_at_install':BOOT, 'targets':targets, 'protected':protected}
    (backup/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    source = Path(__file__).read_bytes()
    (backup/'rollback.py').write_bytes(source)
    os.sync()
    try:
        for entry, data in zip(targets,[new_xorg,new_uenv]):
            target = root/entry['path'].lstrip('/')
            assert digest(target.read_bytes()) == entry['before_sha256']
            writer(target,data,entry['mode'])
            assert digest(target.read_bytes()) == entry['after_sha256']
        for name, expected in protected.items():
            assert digest((root/name.lstrip('/')).read_bytes()) == expected, name
        os.sync()
    except BaseException:
        rollback(root)
        raise
    result = {'status':'INSTALLED_PENDING_RESTART', 'boot_id':BOOT, 'backup':str(backup),
              'targets':targets, 'protected_files_unchanged':True,
              'system_reboot_sent':False, 'services_restarted':0, 'movement_commands_sent':0}
    (backup/'installation.json').write_text(json.dumps(result,indent=2)+'\n')
    os.sync()
    return result

if __name__ == '__main__':
    assert os.uname().machine == 'aarch64'
    assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == CID
    action = sys.argv[1] if len(sys.argv)>1 else 'install'
    assert action in ['install','rollback']
    if action == 'install':
        assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
        assert Path('/sys/module/drm_kms_helper/parameters/fbdev_emulation').read_text().strip() == 'Y'
        print(json.dumps(install()),flush=True)
    else:
        print(json.dumps(rollback()),flush=True)
