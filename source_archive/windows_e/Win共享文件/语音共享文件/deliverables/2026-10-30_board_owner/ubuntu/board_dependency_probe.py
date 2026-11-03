"""Read-only ARM inventory; no imports of ML engines, devices, or private stores."""
import importlib.util
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import shutil
import sys
import sysconfig
import urllib.request


def command(args):
    return subprocess.check_output(args, text=True, timeout=8).strip()


def main():
    ui = dict(line.split('=', 1) for line in command([
        'systemctl', 'show', 'aura-avatar-ui.service', '-p', 'MainPID',
        '-p', 'ActiveState', '-p', 'ExecStart']).splitlines() if '=' in line)
    pid = int(ui['MainPID'])
    argv = Path('/proc/%s/cmdline' % pid).read_bytes().decode().rstrip('\0').split('\0')
    config_path = Path(argv[argv.index('--config') + 1])
    config = json.loads(config_path.read_text())
    runtime = Path(config['runtime'])
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state', timeout=4) as response:
        state = json.load(response)
    hands = state.get('handsfree_dialogue', {})
    pan = state.get('manual_pan', {})
    packages = {}
    for name in ('numpy', 'sherpa_onnx', 'onnxruntime', 'scipy', 'sounddevice',
                 'torch', 'torchaudio', 'speechbrain', 'silero_vad', 'webrtcvad', 'gi'):
        try:
            spec = importlib.util.find_spec(name)
            packages[name] = {'present': spec is not None,
                              'origin': spec.origin if spec is not None else None}
            if spec is not None:
                try:
                    packages[name]['version'] = importlib.metadata.version(name.replace('_', '-'))
                except importlib.metadata.PackageNotFoundError:
                    packages[name]['version'] = 'metadata_unavailable'
        except Exception as exc:
            packages[name] = {'present': False, 'error': type(exc).__name__}
    resources = []
    # Only public model resource metadata; no database or identity-template reads.
    roots = [runtime / 'aura/models', Path('/home/root/aura/models'),
             Path('/home/root/models'), Path('/opt/aura/models')]
    known = {'model.int8.onnx', 'tokens.txt', 'gtcrn_simple.onnx', 'silero_vad.onnx',
             'embedding_model.ckpt', 'hyperparams.yaml', 'gtcrn.onnx'}
    for root in roots:
        if not root.is_dir() or root.is_symlink():
            continue
        for current, dirs, files in os.walk(str(root), followlinks=False):
            dirs[:] = [d for d in dirs if not Path(current, d).is_symlink()
                       and len(Path(current, d).relative_to(root).parts) <= 5]
            for name in files:
                path = Path(current, name)
                if name not in known or path.is_symlink():
                    continue
                if not any(key in str(path).lower() for key in ('asr', 'paraformer', 'gtcrn', 'vad', 'ecapa')):
                    continue
                resources.append({'path': str(path), 'bytes': path.stat().st_size})
    cpu = [line for line in Path('/proc/cpuinfo').read_text().splitlines()
           if line.startswith(('Hardware', 'model name', 'CPU architecture', 'CPU part'))]
    mem = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    result = dict(readonly=True, model_loads=0, hardware_actions=0,
                  python=sys.version, machine=platform.machine(), cpu_count=os.cpu_count(),
                  libc=os.confstr('CS_GNU_LIBC_VERSION'), wheel_platform=sysconfig.get_platform(),
                  disk={str(p):dict(zip(('total','used','free'),shutil.disk_usage(str(p))))
                        for p in (Path('/home/root'),Path('/tmp'))},
                  cpu=cpu, memory={k: mem[k].strip() for k in ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree')},
                  loadavg=Path('/proc/loadavg').read_text().strip(), packages=packages,
                  model_search_roots=[str(p) for p in roots], resources=resources,
                  boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  ui_pid=pid, actual_config=str(config_path), actual_runtime=str(runtime),
                  pins=len(config.get('component_sha256', {})),
                  state={k: state.get(k) for k in ('phase', 'playing', 'audio_output_state')},
                  listening=hands.get('enabled'), microphone_open=hands.get('microphone_open'),
                  pan={k: pan.get(k) for k in ('state', 'pulse_us', 'automatic_following')})
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
