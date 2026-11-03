#!/usr/bin/env python3
"""Rebuild the fixed DFX source using an explicit installed SDK; never install outputs."""
import argparse
import json
from pathlib import Path
import re
import shutil
from common import PACKAGE, Run, clean_env, lock, require, sha, verify_fixed_sources


def symbols(text):
    for line in text.splitlines():
        words = line.split()
        if len(words) >= 8 and words[0].rstrip(':').isdigit():
            yield {'bind': words[4], 'ndx': words[6], 'name': words[7]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--libdfx', type=Path, required=True)
    parser.add_argument('--chrpath', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--runtime-root', type=Path)
    parser.add_argument('--qemu', type=Path)
    args = parser.parse_args()
    require(1 <= args.jobs <= 16, 'Choose 1..16 jobs according to CPU and memory')
    require(bool(args.runtime_root) == bool(args.qemu), 'Supply runtime-root and qemu together')
    work = args.workspace.resolve()
    versions = lock()
    prepared = json.loads((work/'logs/prepare_sources/status.json').read_text())
    require(prepared['passed'] and prepared['source_lock_sha256'] == sha(PACKAGE/'config/source_lock.json'),
            'Source preparation did not pass for this source lock')
    require(sha(args.libdfx) == versions['link_libdfx_sha256'], 'Link-time libdfx differs from the tested image')
    sdk = args.sdk.resolve()
    cross = str(sdk/'bin/aarch64-linux-gnu-')
    cmake = sdk/'x86_64-petalinux-linux/usr/bin/cmake'
    for tool in [Path(cross+'gcc'), Path(cross+'strip'), Path(cross+'readelf'), cmake, args.chrpath]:
        require(tool.is_file(), 'Missing tool: ' + str(tool))
    run = Run(work/'logs/build_dfx', 'New host-only DFX build; candidate not promoted or deployed')
    env = clean_env()
    try:
        verify_fixed_sources(work, 'dfx_mgr')
        compiler = run.command('compiler', [cross+'gcc', '--version'], work, env)
        require('11.2.0' in compiler, 'Compiler differs from the measured GCC 11.2.0 baseline')
        run.command('cmake-version', [cmake, '--version'], work, env)
        deps = work/'build_deps'
        (deps/'include/libdrm').mkdir(parents=True, exist_ok=False)
        (deps/'lib').mkdir()
        shutil.copy2(work/'sources/libdfx/src/include/libdfx.h', deps/'include/libdfx.h')
        for header in sorted((sdk/'aarch64-xilinx-linux/usr/include/drm').glob('*.h')):
            shutil.copy2(header, deps/'include/libdrm'/header.name)
        require((deps/'include/libdrm/drm.h').is_file(), 'SDK DRM headers missing')
        shutil.copy2(args.libdfx, deps/'lib/libdfx.so.1.0')
        (deps/'lib/libdfx.so').symlink_to('libdfx.so.1.0')
        build = work/'build/dfx'
        require(not build.exists(), 'Refusing to reuse a build directory')
        run.command('configure', [cmake, '-S', work/'sources/dfx_mgr', '-B', build,
            '-G', 'Unix Makefiles', '-DCMAKE_SYSTEM_NAME=Linux', '-DCMAKE_SYSTEM_PROCESSOR=aarch64',
            '-DCMAKE_C_COMPILER='+cross+'gcc', '-DCMAKE_ASM_COMPILER='+cross+'gcc',
            '-DCMAKE_SYSROOT='+str(sdk/'aarch64-xilinx-linux'),
            '-DCMAKE_INCLUDE_PATH='+str(deps/'include'), '-DCMAKE_LIBRARY_PATH='+str(deps/'lib'),
            '-D_deps=dfx', '-DCMAKE_BUILD_TYPE=Debug', '-DWITH_STATIC_LIB=ON', '-DWITH_SHARED_LIB=OFF',
            '-DCMAKE_C_FLAGS=-O2 -fPIC -fstack-protector-strong -D_FORTIFY_SOURCE=2 -mbranch-protection=standard',
            '-DCMAKE_EXE_LINKER_FLAGS=-Wl,-z,relro,-z,now'], work, env)
        run.command('compile', [cmake, '--build', build, '--parallel', str(args.jobs),
                               '--target', 'dfx-mgrd-static', 'dfx-mgr-client-static'], work, env)
        out = work/'artifacts/dfx'
        out.mkdir(parents=True, exist_ok=False)
        records = []
        for name in ['dfx-mgrd', 'dfx-mgr-client']:
            shutil.copy2(build/'example/sys/linux'/(name+'-static'), out/(name+'.debug'))
            shutil.copy2(out/(name+'.debug'), out/name)
            run.command('strip-'+name, [cross+'strip', '--strip-debug', out/name], work, env)
            run.command('rpath-'+name, [args.chrpath, '-d', out/name], work, env)
            elf = run.command('elf-'+name, [cross+'readelf', '-h', '-l', '-d', '-V', out/name], work, env)
            require('AArch64' in elf and '/lib/ld-linux-aarch64.so.1' in elf, 'Unexpected target ELF')
            require(not re.search(r'\((?:RPATH|RUNPATH)\)', elf), 'Build RPATH remains')
            records.append({'path': str(out/name), 'bytes': (out/name).stat().st_size,
                            'sha256': sha(out/name), 'board_verified_this_run': False,
                            'dynamic_dependencies': re.findall(r'\(NEEDED\).*\[(.*?)\]', elf)})
        run.state['artifacts'] = records
        if args.runtime_root:
            image = args.runtime_root.resolve()
            requirements = json.loads((PACKAGE/'config/runtime_requirements.json').read_text())
            exports = set()
            for item in requirements['tested_libraries']:
                library = image/item['image_path'].lstrip('/')
                require(sha(library) == item['sha256'], 'Runtime library mismatch: '+str(library))
                data = run.command('runtime-symbols-'+library.name,
                                   [cross+'readelf', '--dyn-syms', '--wide', library], work, env)
                for s in symbols(data):
                    if s['ndx'] != 'UND' and s['bind'] in ('GLOBAL', 'WEAK'):
                        exports.add(s['name'].replace('@@', '@'))
                        if '@@' in s['name'] or '@' not in s['name']:
                            exports.add(s['name'].split('@')[0])
            for record in records:
                binary = Path(record['path'])
                data = run.command('imports-'+binary.name,
                                   [cross+'readelf', '--dyn-syms', '--wide', binary], work, env)
                imports = sorted({s['name'] for s in symbols(data) if s['ndx']=='UND' and s['bind']=='GLOBAL'})
                unresolved = [s for s in imports if s not in exports]
                require(not unresolved, 'Unresolved strong imports: '+repr(unresolved))
                loader = run.command('loader-'+binary.name, [args.qemu, '-L', image,
                    image/'lib/ld-linux-aarch64.so.1', '--inhibit-cache', '--library-path',
                    str(image/'usr/lib')+':'+str(image/'lib'), '--list', binary], work, env)
                require('not found' not in loader, 'Image loader cannot resolve libraries')
                record.update(strong_imports=len(imports), unresolved_strong_imports=unresolved,
                              original_image_loader_list_passed=True)
            run.state['offline_image_abi_checked'] = True
        else:
            run.state['offline_image_abi_checked'] = False
        run.finish(True)
    except Exception as error:
        run.finish(False, error)
        raise
    print(json.dumps({'passed': True, 'artifacts': records, 'board_access': False}))


if __name__ == '__main__':
    main()
