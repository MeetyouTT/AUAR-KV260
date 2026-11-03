import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
SHARED=Path('/home/ghmd/Win共享文件/语音共享文件/aura')
PREVIOUS=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_vision_start')
LIVE=Path('/home/ghmd/aura-dpu-vision-20261021/live-source')
command=['docker','run','--rm','--network','none','--cpus','2','--memory','2g',
    '--pids-limit','128','--security-opt','no-new-privileges','--cap-drop','ALL',
    '--user',str(os.getuid())+':'+str(os.getgid()),'-w','/implementation',
    '-e','PYTHONPATH=/implementation/candidate/aura/board/vision:/previous/source:/shared:/pydeps']
for host,guest in [(ROOT,'/implementation'),(SHARED,'/shared'),(PREVIOUS,'/previous'),(LIVE,'/live'),
                  (Path('/home/ghmd/aura-identity-dpu-check-20261018/python-deps'),'/pydeps')]:
    command.extend(['-v',str(host)+':'+guest+':ro'])
command.extend(['--entrypoint','/bin/bash','xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106','-lc',
    'source /opt/vitis_ai/conda/etc/profile.d/conda.sh && conda activate vitis-ai-pytorch && '
    'python -B -m unittest discover -s tests -v'])
raise SystemExit(subprocess.call(command))
