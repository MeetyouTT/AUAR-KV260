"""Run one isolated command using the existing pinned Vitis AI 3.0 CPU image."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess

IMAGE = 'xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('script')
    p.add_argument('arguments', nargs=argparse.REMAINDER)
    args = p.parse_args()
    source = Path(__file__).resolve().parent
    if Path(args.script).name != args.script or not (source / args.script).is_file():
        p.error('Script must be an existing file in this source directory')
    private = Path('/home/ghmd/aura-dpu-vision-20261021')
    work = private / 'work'
    work.mkdir(parents=True, exist_ok=True)
    (work / 'arch.json').write_text('{"fingerprint":"0x101000056010407"}\n')
    models = Path('/home/ghmd/Win共享文件/语音共享文件/aura/models/vision')
    legacy = Path('/home/ghmd/aura-identity-dpu-check-20261018')
    runtime = Path('/home/ghmd/Win共享文件/语音共享文件/aura')
    mounts = [(source, '/source', 'ro'), (work, '/work', 'rw'),
              (models, '/models', 'ro'), (legacy, '/legacy', 'ro'),
              (legacy / 'python-deps', '/deps', 'ro'),
              (private / 'private-data', '/data', 'ro'), (runtime, '/aura', 'ro')]
    mounts.extend([(private / 'live-source', '/live', 'ro'),
                   (source.parent / 'candidate' / 'aura', '/candidate', 'ro')])
    command = ['docker', 'run', '--rm', '--network', 'none', '--cpus', '4', '--memory', '8g',
               '--pids-limit', '512', '--security-opt', 'no-new-privileges', '--cap-drop', 'ALL',
               '--user', str(os.getuid()) + ':' + str(os.getgid()), '-w', '/work',
               '-e', 'PYTHONPATH=/deps:/legacy:/source:/aura',
               '-e', 'TORCH_EXTENSIONS_DIR=/work/torch-extensions']
    for host, guest, mode in mounts:
        command.extend(['-v', str(host) + ':' + guest + ':' + mode])
    inner = 'source /opt/vitis_ai/conda/etc/profile.d/conda.sh && conda activate vitis-ai-pytorch && '
    inner += shlex.join(['python', '-B', '/source/' + args.script] + args.arguments)
    command.extend(['--entrypoint', '/bin/bash', IMAGE, '-lc', inner])
    raise SystemExit(subprocess.run(command).returncode)


if __name__ == '__main__':
    main()
