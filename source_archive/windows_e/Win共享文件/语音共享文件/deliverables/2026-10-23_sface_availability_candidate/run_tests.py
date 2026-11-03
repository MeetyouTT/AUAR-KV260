"""Run against an existing offline image; never install host dependencies."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
arguments = sys.argv[1:]
baseline = '--baseline' in arguments
if baseline:
    arguments.remove('--baseline')
command = ['docker', 'run', '--rm', '--network', 'none', '--cpus', '2', '--memory', '2g',
           '--pids-limit', '128', '--security-opt', 'no-new-privileges', '--cap-drop', 'ALL',
           '--user', str(os.getuid())+':'+str(os.getgid()), '-w', '/work',
           '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'AURA_SHARED_SOURCE=/shared',
           '-e', 'AURA_LIVE_SOURCE=/live', '-e', 'AURA_DPU_SOURCE=/previous/candidate/aura',
           '-e', 'PYTHONPATH=/work/tests:/shared:/pydeps']
if baseline:
    command.extend(['-e', 'AURA_CANDIDATE_SOURCE=/work/baseline/aura'])
for host, guest in ((ROOT, '/work'),
                   (Path('/home/ghmd/Win共享文件/语音共享文件/aura'), '/shared'),
                   (Path('/home/ghmd/aura-dpu-vision-20261021/live-source'), '/live'),
                   (Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_vision_start'), '/previous'),
                   (Path('/home/ghmd/aura-identity-dpu-check-20261018/python-deps'), '/pydeps')):
    command.extend(['-v', str(host)+':'+guest+':ro'])
tests = arguments or ['discover', '-s', 'tests', '-p', 'test_feature_availability.py', '-v']
command.extend(['--entrypoint', '/bin/bash', 'xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106',
                '-lc', 'source /opt/vitis_ai/conda/etc/profile.d/conda.sh && '
                'conda activate vitis-ai-pytorch && exec python -B -m unittest "$@"', 'tests', *tests])
raise SystemExit(subprocess.call(command))
