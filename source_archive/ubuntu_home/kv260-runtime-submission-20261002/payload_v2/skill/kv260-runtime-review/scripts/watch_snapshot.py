#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read one PID's watches and memory. Root arguments support isolated offline fixtures."""
import argparse
import datetime
import json
from pathlib import Path
import re


def process_start(path):
    # The comm field can contain spaces and parentheses; field 22 is starttime.
    tail = path.read_text().rsplit(')', 1)[1].split()
    return tail[19]


def status_values(text):
    values = {}
    for line in text.splitlines():
        if ':' in line:
            name, value = line.split(':', 1)
            values[name] = value.strip()
    return values


def collect(pid, proc_root, sys_root):
    process = proc_root/str(pid)
    result = {'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'pid':pid, 'proc_root':str(proc_root), 'sys_root':str(sys_root),
              'snapshot_complete':False, 'errors':[], 'inotify_fds':{}}
    try:
        before = process_start(process/'stat')
        state = status_values((process/'status').read_text())
        result.update(process_name=state.get('Name'), process_start_ticks=before,
                      vmrss=state.get('VmRSS'), vmsize=state.get('VmSize'))
        for path in sorted((process/'fdinfo').iterdir()):
            try:
                text = path.read_text()
            except OSError as error:
                result['errors'].append({'path':str(path),'error':str(error)})
                continue
            watches = []
            for line in text.splitlines():
                if line.startswith('inotify '):
                    match = re.search(r'\bwd:([0-9a-fA-F]+)\b', line)
                    if not match:
                        result['errors'].append({'path':str(path),'error':'Unrecognized inotify wd'})
                    else:
                        watches.append(int(match.group(1),16))
            if watches:
                result['inotify_fds'][path.name] = {
                    'watch_lines':len(watches),'unique_watches':len(set(watches)),
                    'wd_hex':sorted({format(w,'x') for w in watches})}
        after = process_start(process/'stat')
        if before != after:
            result['errors'].append({'error':'PID replaced during snapshot'})
        result['kernel_watch_count'] = sum(v['unique_watches'] for v in result['inotify_fds'].values())
        memory = status_values((proc_root/'meminfo').read_text())
        result['memory'] = {key:memory.get(key) for key in
                            ['MemTotal','MemAvailable','Slab','SReclaimable','SUnreclaim']}
        result['boot_id'] = (proc_root/'sys/kernel/random/boot_id').read_text().strip()
        module = sys_root/'module/zocl'
        if module.is_dir():
            result['zocl'] = {
                name:(module/name).read_text().strip() if (module/name).is_file() else None
                for name in ['srcversion','refcnt']}
            result['zocl']['parameters'] = {
                path.name:path.read_text().strip() for path in (module/'parameters').glob('*') if path.is_file()}
        else:
            result['zocl'] = None
        result['snapshot_complete'] = not result['errors']
    except (OSError, ValueError, IndexError) as error:
        result['errors'].append({'error':str(error)})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--proc-root', type=Path, default=Path('/proc'))
    parser.add_argument('--sys-root', type=Path, default=Path('/sys'))
    args = parser.parse_args()
    if args.pid <= 0:
        parser.error('pid must be positive')
    result = collect(args.pid, args.proc_root, args.sys_root)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['snapshot_complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
