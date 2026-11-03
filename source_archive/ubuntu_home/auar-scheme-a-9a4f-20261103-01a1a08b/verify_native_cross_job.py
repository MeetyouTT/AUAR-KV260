"""Create a temporary cross SDK from the known offline image's development files only."""
import os,subprocess,sys,shutil,re,json,time
from pathlib import Path
qa=Path(sys.argv[1]);out=qa/'native-sdk';out.mkdir(exist_ok=False)
h=Path('/home/ghmd');img=h/'kv260-sd-backup-20261003/offline-inspection/root.original.ext4'
ccbase=h/'Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin'
cmake=h/'Xilinx_2022.2/Vitis/2022.2/tps/lnx64/cmake-3.21.4/bin'
sysroot=out/'sysroot';(sysroot/'usr').mkdir(parents=True);(sysroot/'usr/lib').mkdir();(sysroot/'lib').mkdir()
def debug(cmd):
    p=subprocess.run(['/usr/sbin/debugfs','-R',cmd,str(img)],capture_output=True)
    if p.returncode or b'File not found' in p.stderr:raise RuntimeError(cmd+' '+p.stderr.decode(errors='replace')[-300:])
    return p.stdout
debug('rdump /usr/include '+str(sysroot/'usr'))
debug('rdump /usr/lib/pkgconfig '+str(sysroot/'usr/lib'))
# Read system ELF libraries, linker scripts and CRT startup objects. No home directories are traversed.
commands=[]
for remote,local in [('/usr/lib',sysroot/'usr/lib'),('/lib',sysroot/'lib')]:
    for row in debug('ls -p '+remote).decode(errors='replace').splitlines():
        parts=row.split('/')
        if len(parts)<7:continue
        name=parts[5]
        if '/' in name or not re.fullmatch(r'[\w.+-]+',name):continue
        if '.so' in name or re.fullmatch(r'[Scrt][\w-]*\.o',name) or name in ['libc_nonshared.a','libpthread_nonshared.a']:
            commands.append('rdump '+remote+'/'+name+' '+str(local))
batch=out/'read-development-libraries.txt';batch.write_text('\n'.join(commands)+'\n')
with (out/'debugfs.log').open('wb') as log:
    subprocess.run(['/usr/sbin/debugfs','-f',str(batch),str(img)],stdout=log,stderr=subprocess.STDOUT,check=True)
# Absolute symlinks in a target sysroot must resolve within that sysroot.
for p in list(sysroot.rglob('*')):
    if p.is_symlink() and os.readlink(str(p)).startswith('/'):
        target=sysroot/os.readlink(str(p)).lstrip('/')
        p.unlink();p.symlink_to(os.path.relpath(str(target),str(p.parent)))
binpath=out/'tools';binpath.mkdir()
for name,compiler in [('cc','aarch64-linux-gnu-gcc'),('cxx','aarch64-linux-gnu-g++')]:
    script=binpath/name
    script.write_text('#!/bin/sh\nexec "'+str(ccbase/compiler)+'" --sysroot="'+str(sysroot)+'" -Wl,-rpath-link,'+str(sysroot/'usr/lib')+' -Wl,-rpath-link,'+str(sysroot/'lib')+' "$@"\n')
    script.chmod(0o755)
toolchain=out/'aarch64.cmake'
toolchain.write_text('set(CMAKE_SYSTEM_NAME Linux)\nset(CMAKE_SYSTEM_PROCESSOR aarch64)\nset(CMAKE_SYSROOT "'+str(sysroot)+'")\nset(CMAKE_C_COMPILER "'+str(binpath/'cc')+'")\nset(CMAKE_CXX_COMPILER "'+str(binpath/'cxx')+'")\nset(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)\nset(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)\nset(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)\n')
env=dict(os.environ,CC=str(binpath/'cc'),CXX=str(binpath/'cxx'),CMAKE_TOOLCHAIN_FILE=str(toolchain),PKG_CONFIG_SYSROOT_DIR=str(sysroot),PKG_CONFIG_LIBDIR=str(sysroot/'usr/lib/pkgconfig'),PATH=str(cmake)+':'+os.environ['PATH'],LC_ALL='C')
(out/'build_env.json').write_text(json.dumps({k:env[k] for k in ['CC','CXX','CMAKE_TOOLCHAIN_FILE','PKG_CONFIG_SYSROOT_DIR','PKG_CONFIG_LIBDIR','PATH']},indent=2))
print('SDK ready, selected library records',len(commands),flush=True)
dest=qa/'native01'
with (qa/'native01.console.log').open('wb') as f:r=subprocess.run(['sh',sys.argv[2]+'/build/build_native.sh',str(dest)],env=env,stdout=f,stderr=subprocess.STDOUT)
(qa/'native01.receipt.json').write_text(json.dumps({'exit_code':r.returncode,'status':'PASS' if r.returncode==0 else 'FAIL','cross_compiler':str(ccbase/'aarch64-linux-gnu-g++'),'board_executed':False},indent=2))
sys.exit(r.returncode)

