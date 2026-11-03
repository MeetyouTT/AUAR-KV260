"""Build the independent read-only batch extension and isolated host checks."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
CC = '/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-gcc'
FLAGS = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic']


def run(arguments):
    subprocess.run(arguments, cwd=str(ROOT), check=True)


run(['gcc', *FLAGS, '-O2', 'test_batch.c', '-o', 'test_batch_host'])
run([str(ROOT/'test_batch_host')])
run(['gcc', *FLAGS, '-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
     'test_batch.c', '-o', 'test_batch_san'])
run([str(ROOT/'test_batch_san')])
run([CC, *FLAGS, '-O2', '-fPIC', '-shared', '-Wl,-z,relro,-z,now',
     'vsrv_mmio.c', '-o', 'libvsrv2_batch.so'])
