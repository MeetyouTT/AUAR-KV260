#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fresh target-board inventory and checks only. Does not switch apps, services or drivers."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True,
                        help='Annex config directory containing source_lock.json and baseline_inputs.json')
    args = parser.parse_args()
    lock = json.loads((args.config/'source_lock.json').read_text())
    originals = json.loads((args.config/'baseline_inputs.json').read_text())
    result = {'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'read_only':True,'board_switch_executed':False,'checks_passed':False,'issues':[],'files':{}}

    def require(condition, message):
        if not condition:
            result['issues'].append(message)

    def command(argv):
        process = subprocess.run(argv, text=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, timeout=30)
        require(process.returncode==0, '{} returned {}: {}'.format(argv[0],process.returncode,process.stderr.strip()))
        return process.stdout

    try:
        require(os.geteuid()==0, 'Run on the target as root to read all process occupancy')
        result['kernel'] = os.uname().release
        require(result['kernel']==lock['kernel_release'], 'Kernel differs from the tested release')
        if result['issues']:
            print(json.dumps(result,indent=2,ensure_ascii=False))
            return 1
        result['boot_id'] = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        result['card_cid'] = Path('/sys/class/block/mmcblk1/device/cid').read_text().strip()
        require(result['card_cid']==lock['tested_card_cid'], 'Card differs from the tested spare card')
        rootdev = os.stat('/').st_dev
        result['root_device'] = Path('/sys/dev/block/{}:{}'.format(os.major(rootdev),os.minor(rootdev))).resolve().name
        require(result['root_device']=='mmcblk1p2', 'Root partition differs from the tested baseline')
        module = Path('/sys/module/zocl')
        result['driver'] = (module/'srcversion').read_text().strip()
        require(result['driver']==lock['stock_zocl_srcversion'], 'Stock ZOCL is not the current driver')
        result['driver_parameters'] = {p.name:p.read_text().strip() for p in (module/'parameters').iterdir()}
        require(result['driver_parameters']=={'enable_xgq_ert':'1'}, 'Driver parameters differ')
        result['module_refcnt'] = (module/'refcnt').read_text().strip()
        result['module_holders'] = [p.name for p in (module/'holders').iterdir()]
        require(result['module_refcnt']=='0' and not result['module_holders'], 'Driver is held or referenced')
        for path, expected in originals.items():
            try:
                actual = digest(path)
                result['files'][path] = {'sha256':actual,'matches':actual==expected}
                require(actual==expected, 'Baseline file changed: '+path)
            except OSError as error:
                result['files'][path] = {'error':str(error),'matches':False}
                require(False, 'Baseline file unavailable: '+path)
        result['service'] = command(['systemctl','show','dfx-mgr.service',
                                    '--property=MainPID,FragmentPath,DropInPaths,ExecStart,ExecStartPre'])
        mainpid = command(['systemctl','show','dfx-mgr.service','--property=MainPID','--value']).strip()
        pid = int(mainpid)
        require(pid>0, 'DFX manager is not running')
        result['daemon_pid'] = pid
        result['daemon_exe'] = os.readlink('/proc/{}/exe'.format(pid))
        require(result['daemon_exe']=='/usr/bin/dfx-mgrd', 'Manager executable differs from the stock path')
        dropins = command(['systemctl','show','dfx-mgr.service','--property=DropInPaths','--value']).strip()
        require(not dropins, 'Manager has service overrides; inspect before any switch')
        text = command(['dfx-mgr-client','-listPackage'])
        result['app_list_raw'] = text
        active = []
        for line in text.splitlines():
            words = line.split()
            if words and re.fullmatch(r'-?\d+,?',words[-1]):
                slot = int(words[-1].rstrip(','))
                if slot != -1:
                    active.append([words[0],slot])
        result['active_apps'] = active
        require(active==[['kv260-benchmark-b4096',0]], 'Current app differs from the restored official baseline')
        clients = []
        for process in Path('/proc').iterdir():
            if not process.name.isdigit():
                continue
            try:
                for fd in (process/'fd').iterdir():
                    try:
                        target = os.readlink(fd)
                    except FileNotFoundError:
                        continue
                    if target.startswith('/dev/dri/'):
                        clients.append({'pid':int(process.name),'fd':fd.name,'target':target})
            except FileNotFoundError:
                continue
        result['drm_clients'] = clients
        require(not clients, 'DRM clients are present; do not unload their driver')
        result['checks_passed'] = not result['issues']
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result['issues'].append(str(error))
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0 if result['checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
