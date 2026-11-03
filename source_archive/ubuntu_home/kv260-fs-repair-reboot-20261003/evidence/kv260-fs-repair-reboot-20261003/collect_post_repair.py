#!/usr/bin/env python3
"""Read-only boot/runtime acceptance plus the original single-image classification."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

OUT = Path('/home/root/kv260-fs-repair-reboot-20261003')
OLD_BOOT = '0251d729-0d3c-44e8-abb9-27121306c081'
EXPECTED_CID = '0353445345333247805558c00401a100'
EXPECTED_FSTAB = '580d18ee47a5dbe98b86ccec7670518c00fe8bc7b58990e186a00d9f559329f0'
STOCK = '/home/root/kv260-runtime-persistent-backup-20261003/original/stock.sha256'
EXPECTED_TOP5 = [(258, '0.949879'), (270, '0.00931229'), (259, '0.00821807'),
                 (257, '0.00498451'), (279, '0.00388194')]

def read(path):
    return Path(path).read_text().strip()

def write_json(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')

def collect(name, argv, timeout=90):
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    (OUT / (name+'.stdout')).write_bytes(result.stdout)
    (OUT / (name+'.stderr')).write_bytes(result.stderr)
    (OUT / (name+'.rc')).write_text(str(result.returncode)+'\n')
    return {'argv':argv,'returncode':result.returncode,'stdout':result.stdout.decode(errors='replace'),
            'stderr':result.stderr.decode(errors='replace')}

def main():
    OUT.mkdir(mode=0o700, exist_ok=True)
    boot = read('/proc/sys/kernel/random/boot_id')
    cid = read('/sys/class/block/mmcblk1/device/cid')
    if boot == OLD_BOOT or cid != EXPECTED_CID:
        raise RuntimeError('new boot or spare-card identity guard failed')
    fstab = Path('/etc/fstab').read_bytes()
    if hashlib.sha256(fstab).hexdigest() != EXPECTED_FSTAB:
        raise RuntimeError('post-repair fstab differs')
    (OUT/'fstab.txt').write_bytes(fstab)
    (OUT/'fstab-backup.txt').write_bytes(Path('/etc/fstab.kv260-pre-dedup-20261003').read_bytes())
    state = {
        'boot_id':boot, 'previous_boot_id':OLD_BOOT, 'card_cid':cid,
        'kernel':read('/proc/sys/kernel/osrelease'), 'cmdline':read('/proc/cmdline'),
        'boot_uptime_seconds':float(read('/proc/uptime').split()[0]),
        'zocl_srcversion':read('/sys/module/zocl/srcversion'),
        'zocl_refcnt':read('/sys/module/zocl/refcnt'),
        'enable_xgq_ert':read('/sys/module/zocl/parameters/enable_xgq_ert'),
        'fstab_sha256':hashlib.sha256(fstab).hexdigest(),
        'fstab_backup_sha256':hashlib.sha256((OUT/'fstab-backup.txt').read_bytes()).hexdigest(),
    }
    write_json('runtime.json',state)
    commands = {
        'kernel-boot':['dmesg'],
        'os-release':['cat','/etc/os-release'],
        'root-mount':['findmnt','-n','-o','SOURCE,FSTYPE,TARGET','/'],
        'boot-mount':['findmnt','-n','-o','SOURCE,FSTYPE,TARGET','/boot'],
        'manager':['systemctl','show','dfx-mgr.service','-p','MainPID','-p','ActiveState',
                   '-p','SubState','-p','Result','-p','ExecMainStatus','-p','ExecStart','-p','DropInPaths'],
        'loader':['systemctl','show','kv260-repaired-zocl.service','-p','ActiveState',
                  '-p','SubState','-p','Result','-p','ExecMainStatus'],
        'apps':['xmutil','listapps'],
        'stock-check':['sha256sum','-c',STOCK],
        'persistent-hashes':['sha256sum','/usr/local/lib/kv260-runtime-repair/dfx-mgrd',
                              '/usr/local/lib/kv260-runtime-repair/zocl.ko'],
        'dpu-query':['xdputil','query'],
    }
    results = {name:collect(name,argv) for name,argv in commands.items()}
    classification = collect('classification',[
        '/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification',
        '/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel',
        '/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg'])
    results['classification'] = classification
    results['full-boot-journal'] = collect('full-boot-journal',[
        'journalctl','-b','--no-pager','-o','short-monotonic'])
    results['service-journal'] = collect('service-journal',[
        'journalctl','-b','-u','dfx-mgr.service','-u','kv260-repaired-zocl.service',
        '--no-pager','-o','short-monotonic'])
    results['failed-units'] = collect('failed-units',[
        'systemctl','--failed','--no-pager','--plain'])
    results['kernel-final'] = collect('kernel-final',['dmesg'])
    write_json('commands.json',{name:{key:value for key,value in result.items()
                                     if key in ('argv','returncode')} for name,result in results.items()})
    combined = classification['stdout'] + classification['stderr']
    top5 = [(int(a),b) for a,b in re.findall(r'r.index (\d+) .*?r.score ([0-9.eE+-]+)',combined)]
    query = json.loads(results['dpu-query']['stdout'])
    kernels = query['kernels']
    journal = results['full-boot-journal']['stdout']
    fat_warnings = [line for line in journal.splitlines()
                    if 'FAT-fs' in line and re.search(r'not properly unmounted|corrupt|error',line,re.I)]
    duplicate_warnings = [line for line in journal.splitlines()
                          if '/boot' in line or 'boot.mount' in line]
    duplicate_warnings = [line for line in duplicate_warnings
                          if re.search(r'duplicate|already exists|File exists|failed to create',line,re.I)]
    entries = [line for line in fstab.decode().splitlines() if line.strip() and
               not line.lstrip().startswith('#') and line.split()[1]=='/boot']
    checks = {
        'new_boot_on_same_spare_card':boot!=OLD_BOOT and cid==EXPECTED_CID,
        'correct_fstab_with_one_boot_entry':state['fstab_sha256']==EXPECTED_FSTAB and len(entries)==1,
        'original_fstab_backup_preserved':state['fstab_backup_sha256']=='b1978c1e094cd260b761afbaab75f0d9e659a78044d1d4fd86807bc44ef158bd',
        'boot_mount_correct':results['boot-mount']['returncode']==0 and results['boot-mount']['stdout'].split()==['/dev/mmcblk1p1','vfat','/boot'],
        'repaired_zocl_loaded':state['zocl_srcversion']=='9BDC942A6014BCCBD1DCB78' and state['enable_xgq_ert']=='1',
        'manager_running_repaired_binary':all(value in results['manager']['stdout'] for value in
            ['ActiveState=active','Result=success','/usr/local/lib/kv260-runtime-repair/dfx-mgrd']),
        'loader_succeeded':all(value in results['loader']['stdout'] for value in
            ['ActiveState=active','Result=success','ExecMainStatus=0']),
        'official_b4096_active':bool(re.search(r'^\s*kv260-benchmark-b4096\s+.*\s0,\s*$',results['apps']['stdout'],re.M)),
        'original_26_hashes_match':results['stock-check']['returncode']==0 and results['stock-check']['stdout'].count(': OK\n')==26,
        'dpu_query_success':results['dpu-query']['returncode']==0,
        'dpu_profile_matches':query['DPU IP Spec']['DPU Core Count']==1 and len(kernels)==1 and all(
            kernels[0][key]==value for key,value in {'DPU Arch':'DPUCZDX8G_ISA1_B4096','DPU Frequency (MHz)':300,
                'cu_addr':'0xa0010000','fingerprint':'0x101000056010407'}.items()),
        'same_image_classification_passed':classification['returncode']==0 and top5==EXPECTED_TOP5,
        'full_journal_collected':results['full-boot-journal']['returncode']==0,
        'no_fat_dirty_warning_in_this_boot':not fat_warnings,
        'no_duplicate_boot_mount_warning':not duplicate_warnings,
    }
    write_json('summary.json',{'checks':checks,'all_passed':all(checks.values()),'runtime':state,
        'boot_entries':entries,'top5':top5,'fat_warning_lines':fat_warnings,
        'duplicate_boot_warning_lines':duplicate_warnings,
        'scope':'single post-filesystem-repair cold boot and original model/image functional acceptance; no additional soak/FPS/actuator test'})
    print(json.dumps({'boot_id':boot,'all_passed':all(checks.values()),'checks':checks}),flush=True)

if __name__=='__main__':
    main()
