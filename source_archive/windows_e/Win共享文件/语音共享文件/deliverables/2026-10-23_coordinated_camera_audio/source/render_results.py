"""Use the installed plotting environment without adding host dependencies."""
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
DELIVERY=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_coordinated_camera_audio')
args=['docker','run','--rm','--network','none','--cpus','2','--memory','1g',
      '--security-opt','no-new-privileges','--cap-drop','ALL','--user',str(os.getuid())+':'+str(os.getgid()),
      '-e','MPLCONFIGDIR=/tmp/aura-mpl','-v',str(ROOT)+':/work:ro','-v',str(DELIVERY)+':/delivery',
      '--entrypoint','/bin/bash','xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106','-lc',
      'source /opt/vitis_ai/conda/etc/profile.d/conda.sh && conda activate vitis-ai-pytorch && '
      'python -B /work/make_results_plot.py /work/completed-trials.json '
      '/delivery/evidence/baseline-120-summary.json /delivery/results']
subprocess.run(args,check=True)
