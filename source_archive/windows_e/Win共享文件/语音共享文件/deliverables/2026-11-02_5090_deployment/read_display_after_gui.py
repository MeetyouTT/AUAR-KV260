"""Read the current X server's display power metadata after GUI startup."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import subprocess

BOOT='903cfade-b93c-48fa-804e-379be1967313'
STARTUP=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert hashlib.sha256(STARTUP.read_bytes()).hexdigest()=='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
assert os.geteuid()==0
config=json.loads(STARTUP.read_bytes());assert config['display']==':0'
unit=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=MainPID,ActiveState,SubState,Job'],capture_output=True,text=True,timeout=5)
assert unit.returncode==0
fields=dict(line.split('=',1) for line in unit.stdout.splitlines() if '=' in line)
assert fields['ActiveState']=='active' and fields['SubState']=='running' and not fields['Job'] and int(fields['MainPID'])>0
x=Path('/proc/1159')
assert (x/'stat').read_text().rsplit(')',1)[1].split()[19]=='1570'
assert hashlib.sha256((x/'cmdline').read_bytes()).hexdigest()=='9c376bebed4708ef2f0141ce51545ac0b669353b74ea4163c2d80d5a50f5be2a'
env=dict(os.environ,DISPLAY=config['display'],HOME=pwd.getpwuid(0).pw_dir)
env.pop('XAUTHORITY',None)
query=subprocess.run(['xset','q'],env=env,capture_output=True,text=True,timeout=8)
assert query.returncode==0
screen=re.search(r'\btimeout:\s*(\d+)\s+cycle:\s*(\d+)',query.stdout)
enabled=re.search(r'\bDPMS is (Enabled|Disabled)\b',query.stdout)
monitor=re.search(r'\bMonitor is (On|Off|Standby|Suspend)\b',query.stdout)
assert screen and enabled and monitor
print(json.dumps({'schema':'aura-display-after-gui-readonly-1',
    'board_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':BOOT,
    'gui_supervisor_pid':int(fields['MainPID']),'x_server_pid':1159,
    'display':':0','xset_query_succeeded':True,'monitor_power':monitor[1],
    'dpms_enabled':enabled[1]=='Enabled','screensaver_timeout_seconds':int(screen[1]),
    'screensaver_cycle_seconds':int(screen[2]),'policy_changed':False,'wake_command_sent':False,
    'images_or_private_data_exported':False,'mutation_requested':False}))
