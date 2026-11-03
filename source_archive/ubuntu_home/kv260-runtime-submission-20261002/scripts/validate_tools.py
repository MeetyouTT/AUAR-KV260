#!/usr/bin/env python3
"""Exercise the new read-only helpers in local fixtures, not on the KV260."""
import errno
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import tarfile
import tempfile
import io

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT/'payload'
SKILL = PAYLOAD/'skill/kv260-runtime-review'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'evidence'/(
        'tools_validation_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'.json'))
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('Refusing to overwrite validation evidence: '+str(args.output))
    results = {'scope':'Offline local fixtures only; no target-board connection or state change',
               'board_verified_this_run':False, 'tests':[], 'passed':False}

    def cli(name, argv, expected):
        process = subprocess.run([sys.executable,'-B']+list(map(str,argv)),
                                 text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        entry = {'name':name,'argv':list(map(str,argv)),'exit_code':process.returncode,
                 'expected_exit_code':expected,'stdout':process.stdout,'stderr':process.stderr}
        results['tests'].append(entry)
        if process.returncode != expected:
            raise RuntimeError('Unexpected exit: '+name)
        return json.loads(process.stdout)

    try:
        with tempfile.TemporaryDirectory(prefix='kv260-annex-fixture-') as directory:
            temp = Path(directory)
            path = temp/'seqpacket.sock'
            with socket.socket(socket.AF_UNIX,socket.SOCK_SEQPACKET) as server:
                server.bind(str(path))
                server.listen(4)
                wrong = cli('socket-wrong-type',[SKILL/'scripts/socket_probe.py','--path',path,'--type','stream'],1)
                if wrong['errno'] != errno.EPROTOTYPE or wrong['ipc_reachable']:
                    raise RuntimeError('Wrong socket type did not report EPROTOTYPE')
                right = cli('socket-correct-type',[SKILL/'scripts/socket_probe.py','--path',path],0)
                if not right['ipc_reachable'] or right['functional_validation'] or right['attempts']!=1:
                    raise RuntimeError('Socket helper overstated functional validation')
            absent = cli('socket-missing',[SKILL/'scripts/socket_probe.py','--path',temp/'missing.sock'],1)
            if absent['errno'] != errno.ENOENT:
                raise RuntimeError('Missing socket was not distinguished')

            proc = temp/'proc'
            pid = proc/'123'
            (pid/'fdinfo').mkdir(parents=True)
            tail = ['0']*20
            tail[0],tail[19] = 'S','8088'
            (pid/'stat').write_text('123 (runtime (worker)) '+' '.join(tail)+'\n')
            (pid/'status').write_text('Name:\tdfx-mgrd\nVmRSS:\t2048 kB\nVmSize:\t8192 kB\n')
            (pid/'fdinfo/3').write_text('pos:\t0\ninotify wd:a ino:101 sdev:1 mask:fc6\ninotify wd:b ino:102 sdev:1 mask:fc6\n')
            (pid/'fdinfo/4').write_text('pos:\t0\ninotify wd:a ino:103 sdev:1 mask:fc6\n')
            (pid/'fdinfo/5').write_text('pos:\t0\nflags:\t0100000\n')
            (proc/'meminfo').write_text('MemTotal: 4096000 kB\nMemAvailable: 3000000 kB\nSlab: 4096 kB\nSReclaimable: 2048 kB\nSUnreclaim: 2048 kB\n')
            (proc/'sys/kernel/random').mkdir(parents=True)
            (proc/'sys/kernel/random/boot_id').write_text('offline-fixture-boot\n')
            sysroot = temp/'sys'
            module = sysroot/'module/zocl'
            (module/'parameters').mkdir(parents=True)
            (module/'srcversion').write_text('FIXTURE_ONLY\n')
            (module/'refcnt').write_text('0\n')
            (module/'parameters/enable_xgq_ert').write_text('1\n')
            snapshot = cli('watches-per-fd',[SKILL/'scripts/watch_snapshot.py','--pid','123',
                                         '--proc-root',proc,'--sys-root',sysroot],0)
            if snapshot['kernel_watch_count']!=3 or snapshot['process_start_ticks']!='8088':
                raise RuntimeError('Watch descriptors not counted per FD, or stat parsed incorrectly')
            missing = cli('missing-pid-is-incomplete',[SKILL/'scripts/watch_snapshot.py','--pid','124',
                                                    '--proc-root',proc,'--sys-root',sysroot],1)
            if missing['snapshot_complete'] or not missing['errors'] or 'kernel_watch_count' in missing:
                raise RuntimeError('Missing PID incorrectly interpreted as zero watches')

            sys.path.insert(0,str(PAYLOAD/'scripts'))
            from prepare_sources import extract_archive
            for name, member in [('path-traversal','../outside.txt'),('absolute-path','/outside.txt')]:
                archive = temp/(name+'.tar')
                with tarfile.open(archive,'w') as packed:
                    info = tarfile.TarInfo(member)
                    info.size=1
                    packed.addfile(info,io.BytesIO(b'x'))
                rejected = False
                try:
                    extract_archive(archive,temp/name)
                except RuntimeError:
                    rejected = True
                if not rejected:
                    raise RuntimeError('Unsafe archive accepted: '+name)
                results['tests'].append({'name':name,'unsafe_member_rejected':True})
            archive = temp/'valid-link.tar'
            with tarfile.open(archive,'w') as packed:
                info=tarfile.TarInfo('include/real.h');info.size=1;packed.addfile(info,io.BytesIO(b'x'))
                info=tarfile.TarInfo('arch/link.h');info.type=tarfile.SYMTYPE;info.linkname='../include/real.h'
                packed.addfile(info)
            extract_archive(archive,temp/'valid-link',allow_symlinks=True)
            if (temp/'valid-link/arch/link.h').read_bytes()!=b'x':
                raise RuntimeError('Valid relative kernel symlink was not preserved')
            results['tests'].append({'name':'safe-relative-kernel-link','passed':True})
            archive = temp/'escape-link.tar'
            with tarfile.open(archive,'w') as packed:
                info=tarfile.TarInfo('link');info.type=tarfile.SYMTYPE;info.linkname='../../outside'
                packed.addfile(info)
            try:
                extract_archive(archive,temp/'escape-link',allow_symlinks=True)
            except RuntimeError:
                results['tests'].append({'name':'escaping-kernel-link','unsafe_member_rejected':True})
            else:
                raise RuntimeError('Escaping kernel symlink accepted')
        refusal = cli('board-preflight-refuses-development-host',
                      [PAYLOAD/'scripts/board_preflight.py','--config',PAYLOAD/'config'],1)
        if refusal['checks_passed'] or refusal['board_switch_executed'] or not refusal['issues']:
            raise RuntimeError('Target preflight incorrectly accepted the development host')
        results['passed']=True
    except Exception as error:
        results['error']=str(error)
    for path in sorted(PAYLOAD.rglob('*.py')):
        # Parse without creating bytecode in the payload or executing target-only code.
        compile(path.read_text(),str(path),'exec')
    results['python_syntax_checked']=True
    args.output.write_text(json.dumps(results,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'passed':results['passed'],'tests':len(results['tests']),
                      'error':results.get('error'),'board_access':False}))
    return 0 if results['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
