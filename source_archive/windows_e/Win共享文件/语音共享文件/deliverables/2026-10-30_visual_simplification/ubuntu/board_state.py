"""Read-only entry/pin/idle/path audit; exports no identity or image payloads."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args):
    return subprocess.check_output(args, text=True, timeout=10).strip()


def unit(name):
    return dict(line.split('=', 1) for line in run([
        'systemctl', 'show', name, '-p', 'MainPID', '-p', 'ExecStart',
        '-p', 'NRestarts', '-p', 'ActiveState', '-p', 'DropInPaths',
        '-p', 'SubState', '-p', 'UnitFileState']).splitlines() if '=' in line)


def proc(pid):
    path = Path('/proc')/str(pid)
    argv = (path/'cmdline').read_bytes().decode().rstrip('\0').split('\0')
    values = (path/'environ').read_bytes().decode().rstrip('\0').split('\0')
    allowed = ('HOME', 'XDG_DATA_HOME', 'XDG_RUNTIME_DIR', 'PYTHONPATH',
               'PYTHONDONTWRITEBYTECODE', 'AURA_RUNTIME', 'AURA_RUNTIME_ROOT',
               'AURA_EVIDENCE_ROOT', 'AURA_STAGE_LOG')
    env = {k:v for k,v in (value.split('=',1) for value in values if '=' in value)
           if k in allowed}
    ticks = (path/'stat').read_text().rsplit(') ',1)[1].split()[19]
    return dict(pid=int(pid), argv=argv, start_ticks=ticks,
                cwd=os.readlink(path/'cwd'), environment=env)


def pointer(path):
    value = dict(path=str(path), exists=path.exists(), symlink=path.is_symlink())
    if path.is_symlink():
        value.update(link=os.readlink(path), resolved=str(path.resolve()))
    return value


def capture():
    ui = unit('aura-avatar-ui.service')
    camera = unit('aura-camera-ui.service')
    actual_proc = proc(ui['MainPID'])
    argv = actual_proc['argv']
    config_path = Path(argv[argv.index('--config')+1])
    config = json.loads(config_path.read_text())
    root = Path(config['runtime'])
    pins = config['component_sha256']
    pending_args = re.search(r'argv\[\]=(.*?);',ui['ExecStart']).group(1).split()
    pending_path = Path(pending_args[pending_args.index('--config')+1])
    pending = json.loads(pending_path.read_text())
    actual_launcher = next(a for a in argv[:argv.index('--config')] if a.endswith('.py'))
    pending_launcher = next(a for a in pending_args[:pending_args.index('--config')] if a.endswith('.py'))
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5) as r:
        state = json.load(r)
    hands = state.get('handsfree_dialogue',{})
    pan = state.get('manual_pan',{})
    safe = (ui['ActiveState']=='active' and camera['ActiveState']=='active'
            and state.get('phase')=='IDLE' and state.get('playing') is False
            and state.get('audio_output_state')=='IDLE_READY'
            and hands.get('enabled') is False and hands.get('microphone_open') is False
            and pan.get('automatic_following') is False and not state.get('error')
            and pan.get('state') in ('READY','FAULT','HOLD','IDLE','DISABLED')
            and not any(pan.get(k) for k in ('busy','moving','active_motion','motion_active'))
            and state.get('ui_settings',{}).get('pending') is False)
    selected = {k:state.get(k) for k in (
        'phase','playing','audio_output_state','portrait_offload','avatar_display',
        'ui_tick_ms','audio_output','device_observer')}
    selected['ui_link'] = state.get('ui_runtime',{}).get('link')
    selected['camera_epoch'] = state.get('ui_runtime',{}).get('snapshot',{}).get('preview',{}).get('camera_epoch')
    launch = json.loads((root/'launch.json').read_text())
    child = proc(launch['pid'])
    paths = ui['DropInPaths'].split()
    candidates = {}
    for stage in Path('/home/root/aura-board-vision-20261030').glob('*'):
        candidate_root = stage/'runtime'
        candidates[str(stage)] = {name:pointer(candidate_root/name)
                                 for name in ('stage.log','managed-runs','launch.json')}
    transactions = []
    for path in Path('/proc').iterdir():
        if not path.name.isdigit() or int(path.name)==os.getpid():
            continue
        try:
            args = (path/'cmdline').read_bytes().decode().rstrip('\0').split('\0')
        except OSError:
            continue
        # Inspect executable/script positions only; never print arbitrary -c payloads.
        script_names = [Path(a).name for a in args[1:3] if a.endswith('.py')]
        if any(n in ('deploy_board.py','deploy_final_board.py','deploy_visual.py',
                     'rollback_visual.py') for n in script_names):
            transactions.append(dict(pid=int(path.name), scripts=script_names))
    return dict(
        boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        ui=ui,camera=camera,actual_proc=actual_proc,child=child,
        camera_proc=proc(camera['MainPID']),actual_config=str(config_path),
        actual_launcher=actual_launcher,actual_runtime=str(root),config=config,pins=pins,
        config_sha256=digest(config_path),actual_launcher_sha256=digest(actual_launcher),
        pending_config=str(pending_path),pending_launcher=pending_launcher,pending=pending,
        pending_config_sha256=digest(pending_path),pending_launcher_sha256=digest(pending_launcher),
        prior_overrides={name:digest(name) for name in paths},
        mismatches=[name for name,sha in pins.items() if digest(root/'aura'/name)!=sha],
        state=selected,listening=hands.get('enabled'),microphone_open=hands.get('microphone_open'),
        pan={k:pan.get(k) for k in ('state','pulse_us','target_us','automatic_following',
                                  'busy','moving','active_motion','motion_active','backend_pid','error')},
        safe=safe,mechanical_sha256=digest(root/'aura/config/pan_manual.local.json'),
        settings={p.name:digest(p) for p in root.glob('*_settings.json')},
        firmware=Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),
        fdt_sha256=digest('/sys/firmware/fdt'),vart=Path('/etc/vart.conf').read_text().strip(),
        active_pointers={name:pointer(root/name) for name in ('stage.log','managed-runs','launch.json')},
        failed_candidate_pointers=candidates,launch=launch,
        detected_deployment_processes=transactions,
        network=dict(address=run(['ip','-br','address']),route=run(['ip','route']),
                     eth0_carrier=Path('/sys/class/net/eth0/carrier').read_text().strip()),
        readonly=True)


if __name__ == '__main__':
    print(json.dumps(capture(),ensure_ascii=True))
