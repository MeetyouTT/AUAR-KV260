#!/usr/bin/env python3
"""Prepare a separate matching kernel and build ZOCL; never load or install modules."""
import argparse
import json
from pathlib import Path
import shutil
from common import PACKAGE, Run, clean_env, lock, require, sha, write_json, verify_fixed_sources
from prepare_sources import extract_archive


def config_values(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            name, value = line.split('=', 1)
            values[name] = value
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            values[line[2:-11]] = 'n'
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'kernel', 'module'])
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--kernel-git', type=Path, help='Required for prepare; fixed, clean linux-xlnx checkout')
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    require(1 <= args.jobs <= 16, 'Choose 1..16 jobs according to CPU and memory')
    versions = lock()
    work = args.workspace.resolve()
    source_state = json.loads((work/'logs/prepare_sources/status.json').read_text())
    require(source_state['passed'] and source_state['source_lock_sha256']==sha(PACKAGE/'config/source_lock.json'),
            'Run prepare_sources first using this source lock')
    sdk = args.sdk.resolve()
    cross = str(sdk/'bin/aarch64-linux-gnu-')
    require(Path(cross+'gcc').is_file(), 'SDK compiler missing')
    run = Run(work/'logs'/('zocl_'+args.phase), 'Isolated host kernel/ZOCL build; no module installation')
    source = work/'sources/linux'
    build = work/'build/kernel'
    env = clean_env()
    env.update(PATH=str(sdk/'bin')+':/usr/bin:/bin', ARCH='arm64', CROSS_COMPILE=cross,
               KBUILD_BUILD_USER='oe-user', KBUILD_BUILD_HOST='oe-host', KBUILD_BUILD_VERSION='1',
               KBUILD_BUILD_TIMESTAMP='Mon Oct 3 07:50:07 UTC 2022')
    make = ['make', '-C', str(source), 'O='+str(build), 'ARCH=arm64', 'CROSS_COMPILE='+cross]
    try:
        verify_fixed_sources(work, 'xrt')
        compiler = run.command('compiler', [cross+'gcc', '--version'], work, env)
        require('11.2.0' in compiler, 'Compiler differs from measured GCC 11.2.0 baseline')
        if args.phase == 'prepare':
            require(args.kernel_git is not None, 'prepare requires --kernel-git')
            require(not source.exists() and not build.exists(), 'Refusing to overwrite kernel source/build')
            tree = args.kernel_git.resolve()
            head = run.command('kernel-commit', ['git', 'rev-parse', 'HEAD'], tree, env).strip()
            require(head == versions['kernel_commit'], 'linux-xlnx commit mismatch')
            changed = run.command('kernel-clean', ['git', 'diff', '--name-only', 'HEAD'], tree, env).strip()
            require(not changed, 'Kernel checkout has tracked changes')
            archive = work/'kernel_source.tar'
            run.command('kernel-export', ['git','archive','--format=tar','--output='+str(archive),head], tree, env)
            run.state['kernel_archive_sha256'] = sha(archive)
            extract_archive(archive, source, allow_symlinks=True)
            build.mkdir(parents=True, exist_ok=False)
            original = PACKAGE/'config/kernel.config'
            require(sha(original)==versions['kernel_config_sha256'], 'Original kernel configuration changed')
            shutil.copy2(original, build/'.config')
            # Match Honister kernel.bbclass without mutating the original checkout.
            (source/'.scmversion').touch(exist_ok=False)
            (build/'.scmversion').touch(exist_ok=False)
            run.command('olddefconfig', make+['olddefconfig'], work, env)
            a, b = config_values(original), config_values(build/'.config')
            changes = {k:{'original':a.get(k),'resolved':b.get(k)}
                       for k in sorted(set(a)|set(b)) if a.get(k)!=b.get(k)}
            run.state['config_changes'] = changes
            require(not (set(changes)-{'CONFIG_CC_VERSION_TEXT'}), 'Unexpected kernel configuration changes')
            run.command('modules-prepare', make+['-j'+str(args.jobs),'modules_prepare'], work, env)
            release = run.command('kernel-release', make+['-s','kernelrelease'], work, env).splitlines()
            require(versions['kernel_release'] in release, 'Kernel release mismatch')
            write_json(build/'prepared.json', {'commit':head, 'source_lock_sha256':sha(PACKAGE/'config/source_lock.json'),
                'resolved_config_sha256':sha(build/'.config'), 'release':versions['kernel_release'],
                'build_timestamp_is_fixed_input':True})
        else:
            prepared = json.loads((build/'prepared.json').read_text())
            require(prepared['source_lock_sha256']==sha(PACKAGE/'config/source_lock.json') and
                    prepared['resolved_config_sha256']==sha(build/'.config'), 'Prepared kernel inputs changed')
            if args.phase == 'kernel':
                run.command('vmlinux-modules', make+['-j'+str(args.jobs),'vmlinux','modules'], work, env)
                require((build/'Module.symvers').is_file() and (build/'Module.symvers').stat().st_size>0,
                        'Complete kernel Module.symvers missing')
                run.state['kernel_dependencies'] = {
                    name:{'sha256':sha(build/name),'bytes':(build/name).stat().st_size}
                    for name in ['vmlinux','Module.symvers','System.map','.config']}
            else:
                kernel_state = json.loads((work/'logs/zocl_kernel/status.json').read_text())
                require(kernel_state['passed'], 'Complete matching kernel build has not passed')
                symvers = kernel_state['kernel_dependencies']['Module.symvers']['sha256']
                require(sha(build/'Module.symvers')==symvers, 'Kernel symbol versions changed')
                module = work/'sources/xrt/src/runtime_src/core/edge/drm/zocl'
                run.command('zocl-module', make+['-j'+str(args.jobs),'M='+str(module),'modules'], work, env)
                out = work/'artifacts/zocl'
                out.mkdir(parents=True, exist_ok=False)
                shutil.copy2(module/'zocl.ko', out/'zocl.debug.ko')
                shutil.copy2(module/'zocl.ko', out/'zocl.ko')
                run.command('strip', [cross+'strip','--strip-debug',out/'zocl.ko'], work, env)
                metadata = run.command('modinfo', ['/sbin/modinfo',out/'zocl.ko'], work, env)
                require(versions['kernel_release'] in metadata, 'Module vermagic mismatch')
                run.command('elf', [cross+'readelf','-h','-S',out/'zocl.ko'], work, env)
                run.state['artifact'] = {'path':str(out/'zocl.ko'),'sha256':sha(out/'zocl.ko'),
                                         'bytes':(out/'zocl.ko').stat().st_size,'board_verified_this_run':False}
        run.finish(True)
    except Exception as error:
        run.finish(False, error)
        raise
    print(json.dumps({'passed':True,'phase':args.phase,'board_access':False}))


if __name__ == '__main__':
    main()
