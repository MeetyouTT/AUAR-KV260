"""Read the new boot's actual service failures before recovery."""
import hashlib,json,re,subprocess
from pathlib import Path
def cmd(a):
 p=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8)
 return {'rc':p.returncode,'text':p.stdout[-9000:]}
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime':Path('/proc/uptime').read_text().split()[0],'cmdline':Path('/proc/cmdline').read_text().strip(),'files_modified':0,'movement_commands_sent':0}
v['units']=cmd(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','ActiveState','-p','MainPID','-p','NRestarts','-p','ExecStart','-p','Result','-p','ExecMainStatus'])
v['camera_log']=cmd(['journalctl','-b','-u','aura-camera-ui.service','--no-pager','-o','cat','-n','35'])
v['gui_log']=cmd(['journalctl','-b','-u','aura-avatar-ui.service','--no-pager','-o','cat','-n','25'])
d=subprocess.check_output(['dmesg'],text=True)
v['kernel_errors']=[x for x in d.splitlines() if re.search(r'error|fail|unknown symbol|invalid module|uvc|video[0-9]|usb.*disconnect|panic|watchdog',x,re.I)][-40:]
v['video_devices']=[p.name for p in Path('/dev').glob('video*')]
v['backup_uenv_sha256']=hashlib.sha256(Path('/boot/aura-hdmi-preinit-20261021/uEnv.before').read_bytes()).hexdigest()
print(json.dumps(v),flush=True)
