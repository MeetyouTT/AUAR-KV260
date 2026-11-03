"""Offline existing image only; no host package installation or device access."""
import os
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
command=['docker','run','--rm','--network','none','--cpus','1','--memory','1g','--pids-limit','128',
    '--security-opt','no-new-privileges','--cap-drop','ALL','--user',str(os.getuid())+':'+str(os.getgid()),
    '-w','/work','-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONPATH=/work/candidate/aura:/work/tests',
    '-v',str(root)+':/work:ro','--entrypoint','/bin/bash',
    'xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106','-lc',
    'source /opt/vitis_ai/conda/etc/profile.d/conda.sh && conda activate vitis-ai-pytorch && exec python -B -m unittest "$@"',
    'tests',*(sys.argv[1:] or ['discover','-s','tests','-v'])]
raise SystemExit(subprocess.call(command))
