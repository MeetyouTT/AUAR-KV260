import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
P=ROOT
T=Path('/home/ghmd/aura-optional-timing-v2-20261022')
SHARED=Path('/home/ghmd/Win共享文件/语音共享文件/aura')
PREVIOUS=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_vision_start')
LIVE=Path('/home/ghmd/aura-dpu-vision-20261021/live-source')
command=['docker','run','--rm','--network','none','--cpus','2','--memory','2g','--pids-limit','128',
    '--security-opt','no-new-privileges','--cap-drop','ALL','--user',str(os.getuid())+':'+str(os.getgid()),
    '-w','/candidate-root','-e','AURA_SHARED_SOURCE=/shared','-e','AURA_LIVE_SOURCE=/live',
    '-e','AURA_DPU_SOURCE=/previous/candidate/aura','-e','AURA_PREVIOUS_DELIVERABLE=/previous',
    '-e','PYTHONPATH=/candidate-root/candidate/aura/board/vision:/previous/source:/shared:/pydeps']
mounts=[(ROOT,'/merged'),(P,'/candidate-root'),(T,'/implementation'),
    (SHARED,'/shared'),(PREVIOUS,'/previous'),(LIVE,'/live'),
    (Path('/home/ghmd/aura-identity-dpu-check-20261018/python-deps'),'/pydeps'),
    (ROOT/'candidate','/candidate-root/candidate'),(ROOT/'candidate','/implementation/candidate')]
for host,guest in mounts:command.extend(['-v',str(host)+':'+guest+':ro'])
command.extend(['--entrypoint','/bin/bash','xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106','-lc',
    'source /opt/vitis_ai/conda/etc/profile.d/conda.sh && conda activate vitis-ai-pytorch && '
    'python -B -m unittest discover -s tests -v && '
    'python -B -m unittest discover -s /implementation/tests -v'])
raise SystemExit(subprocess.call(command))
