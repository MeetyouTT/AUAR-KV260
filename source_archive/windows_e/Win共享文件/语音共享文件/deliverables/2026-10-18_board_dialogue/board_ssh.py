"""Explicit project SSH transport; uses a host-local private key and known host verification."""
from pathlib import Path
import os
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
KEY=Path(os.environ.get('AURA_BOARD_SSH_KEY', str(Path.home()/'.ssh/aura_5090_board_ed25519')))
KNOWN_HOSTS=Path(os.environ.get('AURA_BOARD_SSH_KNOWN_HOSTS', str(Path.home()/'.ssh/aura_migration_known_hosts')))
SSH=shutil.which('ssh.exe') or shutil.which('ssh')

def ssh(command, script=None, timeout=25):
    if not SSH or not KEY.is_file() or not KNOWN_HOSTS.is_file():
        raise RuntimeError('Configure host-local SSH executable, private key and verified known-hosts file')
    result=subprocess.run([SSH,'-i',str(KEY),'-o','UserKnownHostsFile='+str(KNOWN_HOSTS),'-o','IdentitiesOnly=yes',
                           '-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=4',
                           'root@192.168.50.2',command],input=script,text=True,encoding='utf-8',
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if result.returncode:raise RuntimeError(result.stderr or result.stdout)
    return result.stdout

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('script',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    value=ssh('python3 -',args.script.read_text(encoding='utf-8'),timeout=40)
    if args.output:args.output.write_text(value,encoding='utf-8')
    print(value.encode('ascii','backslashreplace').decode(),end='')
