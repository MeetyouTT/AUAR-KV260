import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
BASELINE=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_vision_start/candidate/aura/board/vision/ui_camera_service.py')
DIAGNOSTIC=Path('/home/ghmd/aura-dpu-audio-diagnosis-20261022/candidate/aura/board/vision/ui_camera_service.py')
command=['docker','run','--rm','--network','none','--cpus','2','--memory','2g','--pids-limit','128',
    '--security-opt','no-new-privileges','--cap-drop','ALL','--user',str(os.getuid())+':'+str(os.getgid()),
    '-w','/candidate-root','-e','AURA_CAPTURE_BASELINE=/baseline_ui.py','-e','AURA_DIAGNOSTIC_BASELINE=/diagnostic_ui.py']
for source,target in ((ROOT,'/candidate-root'),(BASELINE,'/baseline_ui.py'),(DIAGNOSTIC,'/diagnostic_ui.py')):
    command.extend(['-v',str(source)+':'+target+':ro'])
command.extend(['--entrypoint','/bin/bash','xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106','-lc',
    'source /opt/vitis_ai/conda/etc/profile.d/conda.sh && conda activate vitis-ai-pytorch && '
    'python -B -m unittest discover -s tests -v'])
raise SystemExit(subprocess.call(command))
