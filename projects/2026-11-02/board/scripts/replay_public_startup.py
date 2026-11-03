"""Replay the two public file consumers in an isolated offline rootfs on Linux."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'build/scripts'))
from public_board_files import verify_public_files

# Only the fixed WAV loader is imported. It reads the manifest and PCM without playing it.
CHECK_CUES = """
import json,sys
from pathlib import Path
data=json.loads(Path(sys.argv[1]).read_text())
sys.path.insert(0,str(Path(sys.argv[1]).parents[1]))
from tools.board_business_gui import local_feedback_provider
gui=local_feedback_provider(data['formal_static_cues']['path'])()
business=local_feedback_provider(data['board_business']['feedback_manifest'])()
assert gui==business and set(gui)=={'arrival','thinking','invitation'}
print(json.dumps({name:{k:row[k] for k in ('sha256','duration_seconds','bytes')} for name,row in gui.items()}))
"""

def camera_checks(staged, metadata):
    service = 'aura-camera-ui.service'
    paths = ['/etc/systemd/system/' + service] + metadata['systemd_order'][service]
    commands = []
    for name in paths:
        for line in (staged / name.lstrip('/')).read_text(encoding='utf8').splitlines():
            key, _, value = line.partition('=')
            if key.strip() == 'ExecStartPre':
                if value.strip():
                    commands.append(value.strip())
                else:
                    commands.clear()
    signatures = [hashlib.sha256(c.encode()).hexdigest() for c in commands]
    if signatures != [rule['command_sha256'] for rule in metadata['camera_prestart']]:
        raise RuntimeError('The effective camera file checks differ from the pinned release')
    result = [shlex.split(c) for c in commands]
    if any(argv[:3] != ['/usr/bin/python3','-B','-c'] or len(argv) != 4 for argv in result):
        raise RuntimeError('Unexpected command in the camera file-check set')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rootfs', type=Path, required=True, help='separate offline tree produced by stage.py')
    parser.add_argument('--out', type=Path, required=True, help='new JSON receipt outside the release')
    args = parser.parse_args()
    staged, out = args.rootfs.resolve(), args.out.resolve()
    bwrap = shutil.which('bwrap')
    if sys.platform != 'linux' or not bwrap:
        parser.error('Linux user namespaces and bubblewrap are needed for this optional replay')
    if staged == Path('/') or not (staged / 'home/root').is_dir() or staged == ROOT or ROOT in staged.parents:
        parser.error('--rootfs must be a separate staged root')
    if out.exists() or ROOT in out.parents or staged in out.parents:
        parser.error('--out must be a new receipt outside the project and staged tree')
    verify_public_files(ROOT, staged=staged)
    manifest = json.loads((ROOT / 'board/config/public_board_resources.json').read_text())
    args_base = [bwrap, '--die-with-parent', '--new-session','--unshare-all','--clearenv','--setenv','PATH','/usr/bin:/bin','--setenv','LANG','C.UTF-8','--setenv','PYTHONDONTWRITEBYTECODE','1']
    for loc in ('/usr', '/bin', '/lib', '/lib64'):
        if Path(loc).is_dir():
            args_base.extend(['--ro-bind',loc,loc])
    args_base.extend(['--dir','/etc','--dir','/home','--ro-bind',str(staged / 'home/root'),'/home/root','--dev','/dev','--proc','/proc','--tmpfs','/tmp','--chdir','/'])
    checked = []
    for index, command in enumerate(camera_checks(staged, manifest), 1):
        subprocess.run(args_base + command, check=True, timeout=30)
        checked.append(index)
    config = manifest['gui_file']['destination']
    p = subprocess.run(args_base + ['/usr/bin/python3','-B','-c',CHECK_CUES,config],text=True,stdout=subprocess.PIPE,check=True,timeout=40)
    result = {'result':'PASS','camera_ExecStartPre_passed':len(checked),'public_inputs':manifest['camera_prestart_unique_paths'],'network_namespace':'isolated','board_device_access':False,'audio_playback':False,'private_database_access':False,'fixed_prompts':json.loads(p.stdout)}
    with out.open('x', encoding='utf8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('PASS: {} original camera checks; GUI and dialogue providers loaded all three WAVs'.format(len(checked)))


if __name__ == '__main__':
    main()
