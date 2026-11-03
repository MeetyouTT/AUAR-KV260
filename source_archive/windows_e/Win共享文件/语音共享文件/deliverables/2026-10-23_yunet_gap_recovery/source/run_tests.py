"""Run fake-only software tests with existing offline container dependencies."""
import os
from pathlib import Path
import subprocess
import sys
import shutil
import tempfile

ROOT = Path(__file__).resolve().parent
SHARED = Path('/home/ghmd/Win共享文件/语音共享文件/aura')
LIVE = Path('/home/ghmd/aura-dpu-vision-20261021/live-source')
PREVIOUS = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_vision_start')
command = ['docker', 'run', '--rm', '--network', 'none', '--cpus', '2', '--memory', '2g',
    '--pids-limit', '128', '--security-opt', 'no-new-privileges', '--cap-drop', 'ALL',
    '--user', str(os.getuid())+':'+str(os.getgid()), '-w', '/candidate-root',
    '-e', 'AURA_SHARED_SOURCE=/shared', '-e', 'AURA_LIVE_SOURCE=/live',
    '-e', 'AURA_DPU_SOURCE=/previous/candidate/aura',
    '-e', 'AURA_FROZEN_SOURCE=/frozen/candidate/aura',
    '-e', 'PYTHONPATH=/candidate-root/tests:/previous/source:/shared:/pydeps']
for host, guest in ((ROOT, '/candidate-root'), (SHARED, '/shared'), (LIVE, '/live'),
        (PREVIOUS, '/previous'), (Path('/home/ghmd/aura-identity-dpu-check-20261018/python-deps'), '/pydeps')):
    command.extend(['-v', str(host)+':'+guest+':ro'])
FROZEN = Path('/home/ghmd/aura-thread-sched-20261022')
temporary = tempfile.TemporaryDirectory(prefix='aura-yunet-regression-')
overlay = Path(temporary.name)/'candidate'
shutil.copytree(FROZEN/'candidate', overlay)
shutil.copytree(ROOT/'candidate', overlay, dirs_exist_ok=True)
for host, guest in ((FROZEN, '/frozen'), (FROZEN/'timing-tests', '/implementation'),
        (overlay, '/implementation/candidate')):
    command.extend(['-v', str(host)+':'+guest+':ro'])
test_command = 'python -B -m unittest discover -s tests -v'
if sys.argv[1:] == ['--regression']:
    test_command = 'python -B run_regressions.py'
elif sys.argv[1:]:
    raise SystemExit('Usage: run_tests.py [--regression]')
command.extend(['--entrypoint', '/bin/bash', 'xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106',
    '-lc', 'source /opt/vitis_ai/conda/etc/profile.d/conda.sh && conda activate vitis-ai-pytorch && '
    + test_command])
try:
    result = subprocess.call(command)
finally:
    temporary.cleanup()
raise SystemExit(result)
