"""Run CPU-only contract tests in the already installed Vitis AI container."""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
SHARED = Path('/home/ghmd/Win共享文件/语音共享文件/aura')
LIVE = Path('/home/ghmd/aura-dpu-vision-20261021/live-source')
PREVIOUS = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_vision_start')
command = ['docker', 'run', '--rm', '--network', 'none', '--cpus', '2', '--memory', '2g',
    '--pids-limit', '128', '--security-opt', 'no-new-privileges', '--cap-drop', 'ALL',
    '--user', str(os.getuid())+':'+str(os.getgid()), '-w', '/candidate-root',
    '-e', 'AURA_SHARED_SOURCE=/shared', '-e', 'AURA_LIVE_SOURCE=/live',
    '-e', 'AURA_DPU_SOURCE=/previous/candidate/aura', '-e', 'AURA_PREVIOUS_DELIVERABLE=/previous']
for host, guest in ((ROOT, '/candidate-root'), (SHARED, '/shared'), (LIVE, '/live'), (PREVIOUS, '/previous')):
    command.extend(['-v', str(host)+':'+guest+':ro'])
command.extend(['--entrypoint', '/bin/bash', 'xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106',
    '-lc', 'source /opt/vitis_ai/conda/etc/profile.d/conda.sh && conda activate vitis-ai-pytorch && '
    'python -B -m unittest discover -s tests -v'])
raise SystemExit(subprocess.call(command))

