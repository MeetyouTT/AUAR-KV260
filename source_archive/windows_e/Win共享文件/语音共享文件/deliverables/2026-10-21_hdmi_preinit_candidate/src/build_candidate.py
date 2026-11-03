"""Build a kernel candidate in fresh local copies; never deploy to the board."""
import hashlib
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
ORIGINAL = Path('/home/ghmd/kv260-runtime-reproduce-20261003c')
CROSS = '/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    candidate = PACKAGE/'src/zynqmp_dp.c'
    digest = sha(candidate)
    root = Path('/home/ghmd/aura-hdmi-preinit-20261021')/digest[:16]
    assert not root.exists(), 'Preserve existing build; inspect its results instead'
    assert shutil.disk_usage(root.parent.parent).free > 15*1024**3
    root.mkdir(parents=True)
    result = dict(source_sha256=digest, workdir=str(root), steps=[],
                  board_deployed=False, active_image_replaced=False)
    (PACKAGE/'evidence/build-workdir.json').write_text(json.dumps(result,indent=2)+'\n')

    def run(name, args, env=None):
        print('Starting '+name,flush=True)
        started = time.monotonic()
        with (root/(name+'.log')).open('xb') as f:
            p = subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,env=env)
        result['steps'].append(dict(name=name,argv=args,exit_code=p.returncode,
                                    seconds=round(time.monotonic()-started,3),
                                    log=str(root/(name+'.log'))))
        (PACKAGE/'evidence/kernel-build.json').write_text(json.dumps(result,indent=2)+'\n')
        if p.returncode:
            raise RuntimeError(name+' failed; inspect '+str(root/(name+'.log')))
        print('Finished '+name,flush=True)

    run('copy-source',['cp','-a','--reflink=auto','--',str(ORIGINAL/'sources/linux'),str(root/'linux')])
    run('copy-build',['cp','-a','--reflink=auto','--',str(ORIGINAL/'build/kernel'),str(root/'build')])
    rel = 'drivers/gpu/drm/xlnx/zynqmp_dp.c'
    assert sha(root/'linux'/rel)==sha(ORIGINAL/'sources/linux'/rel)
    (root/'linux'/rel).write_bytes(candidate.read_bytes())
    # These generated wrappers belong to the fresh copy only.
    source_link = root/'build/source'
    assert source_link.is_symlink()
    source_link.unlink()
    source_link.symlink_to(root/'linux')
    (root/'build/Makefile').write_text('include '+str(root/'linux/Makefile')+'\n')
    (root/'build/.config').write_bytes((PACKAGE/'evidence/running.config').read_bytes())
    env = dict(os.environ, KBUILD_BUILD_USER='oe-user', KBUILD_BUILD_HOST='oe-host',
               KBUILD_BUILD_TIMESTAMP=datetime.now(timezone.utc).strftime('%a %b %d %H:%M:%S UTC %Y'))
    base = ['make','-C',str(root/'linux'),'O='+str(root/'build'),
            'ARCH=arm64','CROSS_COMPILE='+CROSS]
    run('olddefconfig',base+['olddefconfig'],env)
    run('kernel-image',base+['-j8','Image'],env)
    image = root/'build/arch/arm64/boot/Image'
    release = (root/'build/include/config/kernel.release').read_text().strip()
    assert release=='5.15.36-xilinx-v2022.2', release
    result.update(image=str(image),image_sha256=sha(image),image_bytes=image.stat().st_size,
                  kernel_release=release,config_sha256=sha(root/'build/.config'),
                  completed=True,physical_fix_verified=False)
    (PACKAGE/'evidence/kernel-build.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
