"""Reproduce the frozen combined suites from this shared artifact layout."""
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
SHARED=ROOT.parents[1]/'aura'
PREVIOUS=ROOT.parent/'2026-10-21_dpu_vision_start'
LIVE=Path(os.environ.get('AURA_LIVE_SOURCE','/home/ghmd/aura-dpu-vision-20261021/live-source'))
DEPS=Path(os.environ.get('AURA_PYTHON_DEPS','/home/ghmd/aura-identity-dpu-check-20261018/python-deps'))
assert SHARED.is_dir() and PREVIOUS.is_dir() and LIVE.is_dir() and DEPS.is_dir(), 'Provide matching recovered source/dependency roots'
command=['docker','run','--rm','--network','none','--cpus','2','--memory','2g','--pids-limit','128',
    '--security-opt','no-new-privileges','--cap-drop','ALL','--user',str(os.getuid())+':'+str(os.getgid()),
    '-w','/candidate-root','-e','AURA_SHARED_SOURCE=/shared','-e','AURA_LIVE_SOURCE=/live',
    '-e','AURA_DPU_SOURCE=/previous/candidate/aura','-e','AURA_PREVIOUS_DELIVERABLE=/previous',
    '-e','PYTHONPATH=/candidate-root/candidate/aura/board/vision:/previous/source:/shared:/pydeps']
for host,guest in [(ROOT/'producer-candidate','/candidate-root'),(ROOT/'timing-candidate','/implementation'),
    (SHARED,'/shared'),(PREVIOUS,'/previous'),(LIVE,'/live'),(DEPS,'/pydeps'),
    (ROOT/'merged-candidate','/candidate-root/candidate'),(ROOT/'merged-candidate','/implementation/candidate')]:
    command.extend(['-v',str(host)+':'+guest+':ro'])
command.extend(['--entrypoint','/bin/bash','xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106','-lc',
    'source /opt/vitis_ai/conda/etc/profile.d/conda.sh && conda activate vitis-ai-pytorch && '
    'python -B -m unittest discover -s tests -v && '
    'python -B -m unittest discover -s /implementation/tests -v'])
raise SystemExit(subprocess.call(command))
