import base64,hashlib,json,os,subprocess
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):
    try:return Path(path).read_text().strip()
    except OSError:return None
def query(argv):
    p=subprocess.run(argv,capture_output=True,text=True,timeout=10)
    if p.returncode:raise RuntimeError('Read-only command failed: '+repr(argv))
    return p.stdout
def service(name):
    text=query(['systemctl','show',name,'--no-pager','--property=ActiveState,SubState,MainPID,NRestarts,ExecMainStatus,Result,WorkingDirectory,FragmentPath,DropInPaths'])
    d=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
    p=Path('/proc')/d['MainPID']
    if d['MainPID']!='0' and p.exists():
        args=(p/'cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
        d['entry_paths']=[a for a in args if a.startswith('/') and (a.endswith('.py') or a==args[0])]
        d['config_argument']=args[args.index('--config')+1] if '--config' in args else None
        d['birth_ticks']=int((p/'stat').read_text().rsplit(')',1)[1].split()[19])
        d['cwd']=os.readlink(p/'cwd')
    paths=[d['FragmentPath']]+d.get('DropInPaths','').split()
    d['unit_file_sha256']={name:sha(name) for name in paths if name and Path(name).is_file()}
    return d
assert os.uname().machine=='aarch64' and os.geteuid()==0
boot=read('/proc/sys/kernel/random/boot_id')
units={name:service(name) for name in ['aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service']}
lock=Path('/run/aura-vsrv.lock');holders=[]
if lock.exists():
    stat=lock.stat();key=f'{os.major(stat.st_dev):02x}:{os.minor(stat.st_dev):02x}:{stat.st_ino}'
    for line in (read('/proc/locks') or '').splitlines():
        fields=line.split()
        if '->' not in fields and len(fields)>5 and fields[5].lower()==key:
            pid=int(fields[4]);p=Path('/proc')/str(pid)
            args=(p/'cmdline').read_bytes().rstrip(b'\0').decode(errors='replace').split('\0') if p.exists() else []
            holders.append({'pid':pid,'mode':fields[3],'type':fields[1],
                'script_paths':[a for a in args if a.startswith('/') and a.endswith('.py')],
                'birth_ticks':int((p/'stat').read_text().rsplit(')',1)[1].split()[19]) if p.exists() else None,
                'mmio_fd_open':any(os.readlink(fd)=='/dev/mem' for fd in (p/'fd').iterdir() if fd.exists()) if p.exists() else None})
fdt=Path('/sys/firmware/fdt').read_bytes()
result={'boot_id':boot,'sd_cid_matches_expected':read('/sys/block/mmcblk1/device/cid')=='0353445345333247805558c00401a100',
 'firmware_name':Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),
 'fpga_state':read('/sys/class/fpga_manager/fpga0/state'),'fdt_sha256':hashlib.sha256(fdt).hexdigest(),
 'fdt_base64':base64.b64encode(fdt).decode(),'vart_conf':Path('/etc/vart.conf').read_text(),
 'services':units,'apps':query(['xmutil','listapps']),
 'ipv4':json.loads(query(['ip','-j','-4','addr','show'])),
 'motion_lock_holders':holders,'motion_lock_exists':lock.exists(),
 'mmio_opened':False,'new_dpu_job_submitted':False,'services_modified':False}
print(json.dumps(result,ensure_ascii=False))
