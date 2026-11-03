"""Check recovery against the frozen retry/runtime behavior in an offline image."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
OLD = Path('/home/ghmd/aura-yunet-recovery-20261023')
command = ['docker', 'run', '--rm', '--network', 'none', '--cpus', '2', '--memory', '2g',
    '--pids-limit', '128', '--security-opt', 'no-new-privileges', '--cap-drop', 'ALL',
    '--user', str(os.getuid())+':'+str(os.getgid()), '-w', '/work',
    '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'AURA_SHARED_SOURCE=/shared',
    '-e', 'AURA_LIVE_SOURCE=/live', '-e', 'AURA_DPU_SOURCE=/previous/candidate/aura',
    '-e', 'AURA_FROZEN_SOURCE=/overlay/aura',
    '-e', 'PYTHONPATH=/old/tests:/previous/source:/shared:/pydeps']
with tempfile.TemporaryDirectory(prefix='aura-bounded-recovery-') as directory:
    directory = Path(directory)
    overlay = directory/'overlay'
    shutil.copytree('/home/ghmd/aura-thread-sched-20261022/candidate', overlay)
    shutil.copytree(OLD/'candidate', overlay, dirs_exist_ok=True)
    shutil.copytree(ROOT/'candidate', overlay, dirs_exist_ok=True)
    work = directory/'work'; work.mkdir()
    # The old bootstrap must resolve tests and candidate to this exact overlay.
    shutil.copytree(OLD/'tests', work/'tests')
    shutil.copytree(OLD/'baseline', work/'baseline')
    shutil.copytree(overlay, work/'candidate')
    for source in (ROOT/'tests').glob('test_*.py'):
        shutil.copyfile(source, work/'tests'/source.name)
    for host, guest in ((work, '/work'), (OLD, '/old'), (overlay, '/overlay'),
        (Path('/home/ghmd/Win共享文件/语音共享文件/aura'), '/shared'),
        (Path('/home/ghmd/aura-dpu-vision-20261021/live-source'), '/live'),
        (Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_vision_start'), '/previous'),
        (Path('/home/ghmd/aura-identity-dpu-check-20261018/python-deps'), '/pydeps')):
        command.extend(['-v', str(host)+':'+guest+':ro'])
    command.extend(['--entrypoint', '/bin/bash', 'xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106',
        '-lc', 'source /opt/vitis_ai/conda/etc/profile.d/conda.sh && '
        'conda activate vitis-ai-pytorch && python -B -m unittest discover -s tests -v'])
    raise SystemExit(subprocess.call(command))
