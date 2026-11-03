#!/usr/bin/env python3
"""Prepare a separate read-only check after the manager test has restored stock."""
import base64
import datetime
import gzip
import hashlib
import json
import shlex
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    continuation = Path((ROOT / 'evidence/BOARD_CONTINUATION_RUN').read_text().strip())
    status = json.loads((continuation / 'controller.result.json').read_text())
    assert status['passed'] and status['original_baseline_restored']
    run = ROOT / 'evidence' / (
        datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') +
        '-fstab-audit')
    run.mkdir(exist_ok=False)
    shutil.copy2(continuation / 'collect_serial.py', run / 'collect_serial.py')
    prefix = (continuation / 'action_sources/17-final-state.state.py').read_text().split(
        "gate('0991D1B457855C8987936E6'", 1)[0]
    code = prefix + '''gate('0991D1B457855C8987936E6','kv260-benchmark-b4096')
manager_guard(False)
assert not OVERRIDE.exists() and not OVERRIDE.parent.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='64083069-98b7-409b-a455-b7b3b7158745'
fstab=Path('/etc/fstab').read_text()
mountinfo=Path('/proc/self/mountinfo').read_text()
mounts=Path('/proc/mounts').read_text()
unit=subprocess.run(['systemctl','show','boot.mount','--property=LoadState,ActiveState,SubState,FragmentPath,SourcePath,Where,What,Result'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
boot_mounts=[s for s in mountinfo.splitlines() if s.split()[4]=='/boot']
boot_proc=[s for s in mounts.splitlines() if s.split()[1]=='/boot']
print('FSTAB_AUDIT '+json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime':Path('/proc/uptime').read_text().strip(),'fstab':fstab,'fstab_sha256':digest('/etc/fstab'),'boot_mountinfo':boot_mounts,'boot_proc_mounts':boot_proc,'boot_unit_exit_code':unit.returncode,'boot_unit':unit.stdout,'manager_pid':manager_pid(),'manager_exe':os.readlink('/proc/%d/exe'%manager_pid()),'driver':Path('/sys/module/zocl/srcversion').read_text().strip(),'active':active_packages(),'original_files':{p:digest(p) for p in INPUTS},'temporary_override_absent':not OVERRIDE.exists(),'test_directory_absent':not Path('/lib/firmware/xilinx/watch-probe-20261003T042453Z').exists()}),flush=True)
'''
    (run / 'audit_source.py').write_text(code)
    encoded = base64.b64encode(gzip.compress(code.encode(), mtime=0)).decode()
    decoder = 'import base64,gzip;exec(gzip.decompress(base64.b64decode(' + repr(encoded) + ')))'
    manifest = [{'id': 'configuration', 'command': 'python3 -B -c ' +
                 shlex.quote(decoder), 'timeout': 180}]
    (run / '21-fstab-audit.commands.json').write_text(
        json.dumps(manifest, indent=2) + '\n')
    (run / 'preparation.json').write_text(json.dumps({
        'scope': 'Read-only fstab, boot mount and restored baseline check',
        'board_mutation_authorized_by_this_manifest': False,
        'collector_sha256': sha(run / 'collect_serial.py'),
        'source_sha256': sha(run / 'audit_source.py'),
        'manifest_sha256': sha(run / '21-fstab-audit.commands.json'),
        'restored_run': str(continuation)
    }, indent=2) + '\n')
    (ROOT / 'evidence/BOARD_FSTAB_AUDIT_RUN').write_text(str(run) + '\n')
    print(run)


if __name__ == '__main__':
    main()
