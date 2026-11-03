#!/usr/bin/env python3
"""Build the unmodified vendor-kernel HID MT driver in an isolated output tree."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
ORIGINAL = Path('/home/ghmd/kv260-runtime-reproduce-20261003c/build/kernel')
SOURCE = Path('/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux')
CROSS = '/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def config(p):
    return {s.split('=', 1)[0]: s.split('=', 1)[1] for s in p.read_text().splitlines()
            if s.startswith('CONFIG_') and '=' in s}


def main():
    live = config(ROOT/'running-kernel.config')
    prepared = config(ORIGINAL/'.config')
    changes = {k for k in set(live)|set(prepared) if live.get(k) != prepared.get(k)}
    assert changes <= {'CONFIG_CC_VERSION_TEXT'}, changes
    assert live['CONFIG_MODULES'] == 'y' and 'CONFIG_MODVERSIONS' not in live
    assert 'CONFIG_HID_MULTITOUCH' not in live
    abi = json.loads((ROOT/'kernel_abi_validation.json').read_text())
    assert (ORIGINAL/'include/config/kernel.release').read_text().strip() == abi['release']
    inputs = {str(p): sha(p) for p in [ORIGINAL/'.config', ORIGINAL/'Module.symvers',
              SOURCE/'drivers/hid/hid-multitouch.c', SOURCE/'drivers/hid/hid-ids.h']}
    work = ROOT/'module-build'
    work.mkdir(exist_ok=False)
    output = work/'kernel'
    output.mkdir()
    for relative in ['include', 'scripts', 'arch/arm64/include']:
        target = output/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(ORIGINAL/relative), str(target), symlinks=True)
    for relative in ['.config', '.scmversion', 'Module.symvers']:
        shutil.copy2(str(ORIGINAL/relative), str(output/relative))
    module = work/'driver'
    module.mkdir()
    for name in ['hid-multitouch.c', 'hid-ids.h']:
        shutil.copy2(str(SOURCE/'drivers/hid'/name), str(module/name))
    (module/'Makefile').write_text('obj-m += hid-multitouch.o\n')
    logs = work/'logs'
    logs.mkdir()
    result = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'complete': False, 'board_loaded': False, 'inputs': inputs,
              'kernel_commit': '19984dd147fa7fbb7cb14b17400263ad0925c189',
              'configuration_differences': sorted(changes), 'commands': []}
    commands = [('make', ['make', '-C', str(SOURCE), 'O='+str(output), 'ARCH=arm64',
                         'CROSS_COMPILE='+CROSS, 'M='+str(module), '-j2', 'modules']),
                ('strip', [CROSS+'strip', '--strip-debug', str(module/'hid-multitouch.ko')]),
                ('modinfo', ['modinfo', str(module/'hid-multitouch.ko')]),
                ('readelf', [CROSS+'readelf', '-h', str(module/'hid-multitouch.ko')]),
                ('undefined', [CROSS+'nm', '-u', str(module/'hid-multitouch.ko')])]
    try:
        for name, argv in commands:
            if name == 'strip':
                shutil.copy2(str(module/'hid-multitouch.ko'), str(module/'hid-multitouch.unstripped.ko'))
            process = subprocess.run(argv, cwd=str(work), stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, timeout=120, text=True)
            log = logs/(name+'.log')
            log.write_text(process.stdout)
            result['commands'].append({'name': name, 'argv': argv, 'exit_code': process.returncode,
                                       'log': str(log), 'sha256': sha(log)})
            print(json.dumps({'step': name, 'exit_code': process.returncode, 'log': str(log)}), flush=True)
            if process.returncode:
                raise RuntimeError(name+' failed: '+process.stdout[-1800:])
        modinfo = (logs/'modinfo.log').read_text()
        vermagic = next(s.split(':', 1)[1].strip() for s in modinfo.splitlines() if s.startswith('vermagic:'))
        assert vermagic == abi['zocl_vermagic'], (vermagic, abi['zocl_vermagic'])
        assert 'Machine:                           AArch64' in (logs/'readelf.log').read_text()
        exported = {s.split()[1] for s in (ORIGINAL/'Module.symvers').read_text().splitlines()}
        undefined = {s.split()[-1] for s in (logs/'undefined.log').read_text().splitlines()}
        assert undefined <= exported, sorted(undefined-exported)
        for path, digest in inputs.items():
            assert sha(path) == digest, 'Original changed: '+path
        candidate = module/'hid-multitouch.ko'
        result.update(complete=True, module=str(candidate), bytes=candidate.stat().st_size,
                      sha256=sha(candidate), vermagic=vermagic,
                      undefined_symbols=len(undefined), all_symbols_in_prepared_kernel=True,
                      original_inputs_unchanged=True)
    except Exception as exc:
        result['error'] = str(exc)
    result['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (ROOT/'module_build_validation.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('commands','inputs')}, ensure_ascii=False), flush=True)
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
