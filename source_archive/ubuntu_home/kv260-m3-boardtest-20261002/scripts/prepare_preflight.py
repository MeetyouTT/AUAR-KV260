#!/usr/bin/env python3
"""Create independent M3 evidence and read-only UART manifests."""
import datetime
import hashlib
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]
REPAIR = Path('/home/ghmd/kv260-overlay-repair-20261002')
M3 = Path('/home/ghmd/kv260-m3-axilite-20261002')
PREVIOUS_RUN = REPAIR / 'evidence/board_validation_20261003T005805Z'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run = ROOT / 'evidence' / stamp
    run.mkdir(parents=True, exist_ok=False)
    collector = PREVIOUS_RUN / 'collect_serial.py'
    (run / 'collect_serial.py').write_bytes(collector.read_bytes())
    (run / '01-preflight.commands.json').write_bytes((REPAIR / 'evidence/board_preflight/01-readonly.commands.json').read_bytes())
    (run / '02-state.commands.json').write_bytes((PREVIOUS_RUN / '02-state.commands.json').read_bytes())
    code = '''import os,json,gzip,shutil,stat,subprocess
from pathlib import Path
assert os.geteuid()==0 and os.uname().release=='5.15.36-xilinx-v2022.2'
assert Path('/sys/class/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
busybox=shutil.which('busybox')
assert busybox
applets=subprocess.check_output([busybox,'--list'],text=True).splitlines()
config=gzip.decompress(Path('/proc/config.gz').read_bytes()).decode()
names=('CONFIG_DEVMEM','CONFIG_STRICT_DEVMEM','CONFIG_IO_STRICT_DEVMEM')
mem=Path('/dev/mem')
previous=Path('/home/root/kv260-zocl-repair-20261003T005805Z/candidate-stage/zocl.ko')
import hashlib
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'proc_root_mounts':[line for line in Path('/proc/mounts').read_text().splitlines() if line.split()[1]=='/'],
 'busybox':busybox,'devmem_applet':'devmem' in applets,
 'dev_mem_character_device':mem.exists() and stat.S_ISCHR(mem.stat().st_mode),
 'kernel_memory_options':[line for line in config.splitlines() if any(line.startswith(n+'=') or line=='# '+n+' is not set' for n in names)],
 'root_free_bytes':shutil.disk_usage('/').free,
 'm3_target_exists':Path('/lib/firmware/xilinx/kv260-benchmark-b4096-m3').exists(),
 'prior_repaired_module_sha256':hashlib.sha256(previous.read_bytes()).hexdigest() if previous.is_file() else None,
 'mmio_access_performed':False},indent=2))
'''
    command = 'python3 -B -c ' + shlex.quote(code)
    assert len(command.encode()) * 4 / 3 + 850 < 3900
    (run / '03-capabilities.commands.json').write_text(json.dumps([
        {'id':'capabilities','command':command,'timeout':90}],indent=2)+'\n')
    inputs = [REPAIR / 'EVIDENCE.sha256', REPAIR / 'BOARD_EVIDENCE.sha256',
        M3 / 'evidence/ARTIFACTS.sha256', M3 / 'evidence/REVIEW.sha256',
        M3 / 'evidence/m3_bundle_review/SUPPLEMENT.sha256']
    metadata = {'created_utc':stamp,'authorization':'User: 那就开始做; bounded M3 validation and original baseline recovery',
        'board_work_directory':'/home/root/kv260-m3-boardtest-'+stamp,
        'collector_sha256':sha(collector),'preserved_indexes':{str(p):sha(p) for p in inputs},
        'prior_repaired_module':'/home/root/kv260-zocl-repair-20261003T005805Z/candidate-stage/zocl.ko',
        'scope':'one M3 load, identity/scratch, same-model inference/performance, restore original driver and official app; no flash/reboot/actuator'}
    (run / 'run.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+'\n')
    pointer = ROOT / 'ACTIVE_RUN'
    assert not pointer.exists(), 'Refusing an existing run'
    pointer.write_text(str(run)+'\n')
    print(json.dumps({'run':str(run),'board_work_directory':metadata['board_work_directory'],'prepared_readonly_phases':3}))


if __name__ == '__main__':
    main()
