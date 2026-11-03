"""Run existing 237-test project suite against this complete candidate overlay."""
import os
import hashlib
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
reference=Path('/home/ghmd/aura-vision-persistent-20261023')
gui_consumer=reference/'candidate/aura/board/identity/spoken_query.py'
assert hashlib.sha256(gui_consumer.read_bytes()).hexdigest()=='9bd7a4f6927fbfe6c130056c66c4f420d11603a9d1fe46d237af9b34f3ac75d7'
command=['docker','run','--rm','--network','none','--cpus','1','--memory','1g','--pids-limit','128',
    '--security-opt','no-new-privileges','--cap-drop','ALL','--user',str(os.getuid())+':'+str(os.getgid()),
    '-w','/work','-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONPATH=/work/tests:/shared:/pydeps',
    '-e','AURA_SHARED_SOURCE=/shared','-e','AURA_LIVE_SOURCE=/live','-e','AURA_DPU_SOURCE=/previous/candidate/aura']
mounts=[(reference,'/work'),(root/'candidate/aura','/work/candidate/aura'),
    # The running GUI is a separate 175-source release. Its actual current
    # consumer was checked by root; the camera's older copy is not deployed GUI.
    (gui_consumer,'/work/candidate/aura/board/identity/spoken_query.py'),
    (Path('/home/ghmd/aura-native-critical-20261024/coherent-baseline/aura'),'/shared'),
    (Path('/home/ghmd/aura-dpu-vision-20261021/live-source'),'/live'),
    (Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_vision_start'),'/previous'),
    (Path('/home/ghmd/aura-identity-dpu-check-20261018/python-deps'),'/pydeps')]
for source,target in mounts:command.extend(['-v',str(source)+':'+target+':ro'])
command.extend(['--entrypoint','/bin/bash','xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106','-lc',
    'source /opt/vitis_ai/conda/etc/profile.d/conda.sh && conda activate vitis-ai-pytorch && exec python -B -m unittest "$@"',
    'tests',*(sys.argv[1:] or ['discover','-s','tests','-v'])])
raise SystemExit(subprocess.call(command))
