"""Install a separately named kernel and reversible uEnv selection; do not reboot."""
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

BOOT = '5cd17bb7-30da-4a4f-bf18-8167508de1f4'
SOURCE = Path('/home/root/aura-hdmi-preinit-20261021/d977bdda5e7c9877/Image.gz')
IMAGE_SHA = '8bfafe019e09143795092e9452dbe1ca1850a865a57306d3e8ac5ed12a212a34'
GZIP_SHA = 'db4b51e28150b3693986a1b836a0a4cbabadc86655a402ef874e3c0d5dbf7e2d'
OLD_IMAGE_SHA = 'b02771b1c6ceca7f07b56a97ab36d79d2f17652c58f9c119ddd1d2ea0e554e71'
OLD_UENV_SHA = '05cd73695dc8797899ee32a02ba5081403f02d5b28b8b89b3b71ffe503279ffe'
NAME = 'Image-aura-hdmi-preinit-8bfafe019e09'
BASE_ARGS = 'earlycon console=ttyPS1,115200 clk_ignore_unused root=/dev/ram0 rw init_fatal_sh=1 cma=1536M'
PAYLOAD = ('kernel_name='+NAME+'\nbootargs='+BASE_ARGS+
           ' zynqmp_dpsub.initial_aux_delay_ms=5000\n'
           'uenvcmd=echo AURA initial AUX delay candidate 8bfafe019e09\n').encode()

ROLLBACK = '''"""Restore the previously bootable kernel selection, preserving both files."""
import hashlib,json,os
from pathlib import Path
root=Path(__file__).resolve().parent
meta=json.loads((root/'before.json').read_text())
target=root.parent/'uEnv.txt'
assert not target.is_symlink()
assert hashlib.sha256(target.read_bytes()).hexdigest()==meta['candidate_uenv_sha256'], 'uEnv changed; inspect it first'
original=(root/'uEnv.before').read_bytes()
assert hashlib.sha256(original).hexdigest()==meta['old_uenv_sha256']
saved=root/'uEnv.candidate.disabled'
assert not saved.exists()
with saved.open('xb') as f:f.write(target.read_bytes())
temporary=root.parent/'uEnv.aura-rollback.pending'
with temporary.open('xb') as f:
 f.write(original);f.flush();os.fsync(f.fileno())
temporary.replace(target);os.sync()
assert target.read_bytes()==original
print(json.dumps({'restored_previous_boot_selection':True,'effective_after_next_boot':True}))
'''


def sha(data):return hashlib.sha256(data).hexdigest()


def units():
    return subprocess.check_output(['systemctl','show','aura-avatar-ui.service',
        'aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID',
        '-p','ActiveState','-p','NRestarts'],text=True,timeout=5)


def main():
    assert os.uname().machine=='aarch64'
    assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert Path('/proc/cmdline').read_text().strip()==BASE_ARGS+' zynqmp_dpsub.power_on_delay_ms=5000'
    assert sha(Path('/boot/Image').read_bytes())==OLD_IMAGE_SHA
    target=Path('/boot/uEnv.txt');old=target.read_bytes()
    assert not target.is_symlink() and sha(old)==OLD_UENV_SHA
    assert not (Path('/boot')/NAME).exists()
    backup=Path('/boot/aura-hdmi-preinit-20261021')
    assert not backup.exists() and not backup.is_symlink()
    assert not SOURCE.is_symlink()
    compressed=SOURCE.read_bytes();assert sha(compressed)==GZIP_SHA
    image=gzip.decompress(compressed)
    assert sha(image)==IMAGE_SHA and image[56:60]==b'ARMd'
    assert b'initial_aux_delay_ms' in image
    assert shutil.disk_usage('/boot').free>len(image)+20*1024*1024
    mounts=[line.split() for line in Path('/proc/mounts').read_text().splitlines()]
    assert any(x[:3]==['/dev/mmcblk1p1','/boot','vfat'] and 'rw' in x[3].split(',') for x in mounts)
    assert sha(Path('/boot/boot.scr').read_bytes())=='9ada4d88212468c12d2710b0fae35df42c4c72134bafa82b2ae5aca82570a7f1'
    protected=['/boot/Image','/boot/system.dtb','/boot/boot.scr','/etc/X11/xorg.conf',
        '/home/root/aura-speech-motion-20261021/922dab49a74f/startup/launcher.py',
        '/home/root/aura-speech-motion-20261021/922dab49a74f/startup/config.json']
    before_hashes={p:sha(Path(p).read_bytes()) for p in protected}
    before_units=units();assert before_units.count('ActiveState=active')==3
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:8783/api/state',timeout=2) as r:s=json.load(r)
    assert s['phase']=='IDLE','Do not change boot setup during an active conversation'
    meta=dict(boot_id=BOOT,old_uenv_sha256=OLD_UENV_SHA,candidate_uenv_sha256=sha(PAYLOAD),
              candidate_image_sha256=IMAGE_SHA,candidate_image_name=NAME,
              protected_hashes=before_hashes,original_kernel_retained='/boot/Image')
    backup.mkdir()
    for name,data in [('before.json',(json.dumps(meta,indent=2)+'\n').encode()),
                      ('uEnv.before',old),('uEnv.candidate',PAYLOAD),
                      ('rollback.py',ROLLBACK.encode())]:
        with (backup/name).open('xb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
    pending=Path('/boot')/(NAME+'.pending')
    with pending.open('xb') as f:
        f.write(image);f.flush();os.fsync(f.fileno())
    assert sha(pending.read_bytes())==IMAGE_SHA
    pending.rename(Path('/boot')/NAME)
    pending=Path('/boot/uEnv.aura-preinit.pending')
    with pending.open('xb') as f:
        f.write(PAYLOAD);f.flush();os.fsync(f.fileno())
    assert target.read_bytes()==old
    pending.replace(target);os.sync()
    assert target.read_bytes()==PAYLOAD
    after_hashes={p:sha(Path(p).read_bytes()) for p in protected}
    assert before_hashes==after_hashes
    result=dict(installed_for_next_boot=True,boot_id=BOOT,kernel_name=NAME,
                image_sha256=IMAGE_SHA,uenv_sha256=sha(PAYLOAD),uenv_text=PAYLOAD.decode(),
                backup=str(backup),original_kernel_retained=True,
                protected_hashes=after_hashes,units_before=before_units,units_after=units(),
                reboots_sent=0,movement_commands_sent=0,physical_fix_verified=False)
    (backup/'install-result.json').write_text(json.dumps(result,indent=2)+'\n');os.sync()
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
