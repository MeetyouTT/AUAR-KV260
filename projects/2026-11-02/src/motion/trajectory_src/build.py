from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'ruckig'
CORE=sorted(str(p) for p in (SOURCE/'src/ruckig').glob('*.cpp') if p.name!='cloud_client.cpp')
COMMON=['-O2','-fPIC','-fvisibility=hidden','-shared','-I'+str(SOURCE/'include'),
        '-Wl,-z,relro,-z,now','-Wl,--exclude-libs,ALL']
def build(compiler,standard,output,extra=()):
    subprocess.run([compiler,standard,*COMMON,*extra,str(ROOT/'aura_trajectory.cpp'),str(ROOT/'compat_runtime.cpp'),*CORE,
                    '-o',str(ROOT/output)],check=True,cwd=str(ROOT))
build('g++','-std=c++2a','libaura_trajectory_compat_host.so')
build('/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-g++',
      '-std=c++20','libaura_trajectory_compat.so')
