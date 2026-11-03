"""Read ASR source presence and SSH policy without reading any credentials."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

def run(args):
    try:p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=4)
    except OSError as exc:return {'exit_code':None,'output':str(exc)}
    return {'exit_code':p.returncode,'output':p.stdout[:5000]}
root=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura')
files={}
for name in ('scripts/start_board_asr.ps1','tools/asr_server.py','common/asr_wire.py','docs/BOARD_ASR.md'):
    p=root/name
    files[name]={'exists':p.is_file(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None}
units=run(['systemctl','show','sshd.service','dropbear.service','-p','Id','-p','LoadState','-p','ActiveState','-p','MainPID'])
listeners=[]
for source in ('/proc/net/tcp','/proc/net/tcp6'):
    for line in Path(source).read_text().splitlines()[1:]:
        fields=line.split()
        if fields[1].rsplit(':',1)[1]=='0016' and fields[3]=='0A':listeners.append({'source':source,'local':fields[1]})
status=run(['passwd','-S','root'])
if status['exit_code']==0:
    fields=status['output'].split()
    status['output']=' '.join(fields[:2])
policy={}
sshd=shutil.which('sshd')
if sshd:
    effective=run([sshd,'-T'])
    keys={'permitrootlogin','passwordauthentication','pubkeyauthentication','permitemptypasswords','authenticationmethods','port'}
    policy={'exit_code':effective['exit_code'],'output':'\n'.join(line for line in effective['output'].splitlines() if line.split(' ',1)[0] in keys)}
processes=[]
for folder in Path('/proc').glob('[0-9]*'):
    try:
        if (folder/'comm').read_text().strip() in ('dropbear','sshd'):
            processes.append((folder/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace'))
    except OSError:pass
print(json.dumps({'runtime':str(root),'files':files,'ssh_services':units,'ssh_listeners':listeners,
    'root_password_status':status,'effective_openssh_policy':policy,'ssh_processes':processes,
    'authorized_keys_present':Path('/home/root/.ssh/authorized_keys').is_file(),
    'verified_access_used_by_this_agent':'UART root console; SSH login not tested'},ensure_ascii=False))
