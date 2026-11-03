"""Explicit project SSH transport; uses a host-local private key and known host verification."""
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
KEY=Path('C:/Users/35870/.codex/visualizations/2026/10/09/01a12110-3ba4-7651-b3d7-2e6560916eb6/board-access-20261018/id_ed25519')

def ssh(command, script=None, timeout=25):
    result=subprocess.run(['C:/Windows/System32/OpenSSH/ssh.exe','-i',str(KEY),'-o','IdentitiesOnly=yes',
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
