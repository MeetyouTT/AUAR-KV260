"""Read X11 power policy through the existing server; never wakes or changes settings."""
import datetime
import hashlib
import json
import os
import pwd
from pathlib import Path
import re
import shlex
import subprocess

BOOT='903cfade-b93c-48fa-804e-379be1967313'
STARTUP=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
STARTUP_SHA='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert not STARTUP.is_symlink()
raw=STARTUP.read_bytes();assert hashlib.sha256(raw).hexdigest()==STARTUP_SHA
config=json.loads(raw)
display=config['display'];assert re.fullmatch(r':[0-9]+(?:\.[0-9]+)?',display)
unit=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=Environment,User,MainPID,ActiveState,Job'],
    capture_output=True,text=True,timeout=5)
assert unit.returncode==0
unit_fields=dict(line.split('=',1) for line in unit.stdout.splitlines() if '=' in line)
assert unit_fields['MainPID']=='0' and unit_fields['ActiveState']=='failed' and not unit_fields['Job']
assert unit_fields.get('User','') in ('','root') and os.geteuid()==0
service_env={}
for token in shlex.split(unit_fields.get('Environment','')):
    if '=' in token:
        key,value=token.split('=',1)
        if key in ('DISPLAY','XAUTHORITY'):service_env[key]=value
if 'DISPLAY' in service_env:assert service_env['DISPLAY']==display

servers=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        args=(p/'cmdline').read_bytes().split(b'\0')
        if not args or not args[0]:continue
        exe=Path(args[0].decode(errors='strict')).name
        if exe not in ('X','Xorg','Xorg.wrap','Xwayland','Xvfb'):continue
        text=[item.decode(errors='strict') for item in args if item]
        displays=[item for item in text[1:] if re.fullmatch(r':[0-9]+(?:\.[0-9]+)?',item)]
        # An Xorg without an explicit :N uses display 0 unless -displayfd is present.
        matches=display in displays or (not displays and display==':0' and '-displayfd' not in text)
        if not matches:continue
        auth=text[text.index('-auth')+1] if '-auth' in text else None
        env_values={}
        for item in (p/'environ').read_bytes().split(b'\0'):
            if item.startswith(b'DISPLAY='):env_values['DISPLAY']=item.split(b'=',1)[1].decode()
            elif item.startswith(b'XAUTHORITY='):env_values['XAUTHORITY']=item.split(b'=',1)[1].decode()
        servers.append({'pid':int(p.name),'executable_basename':exe,'auth_argument':auth,
            'access_control_disabled_argument':'-ac' in text,
            'display_argument_explicit':display in displays,'selected_environment':env_values,
            'birth_ticks':(p/'stat').read_text().rsplit(')',1)[1].split()[19],
            'command_sha256':hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()})
    except (FileNotFoundError,ProcessLookupError):continue
assert len(servers)==1,'Require one exact current X server'
server=servers[0]
selected_auth=service_env.get('XAUTHORITY') or server['auth_argument'] or server['selected_environment'].get('XAUTHORITY')
auth_source=('gui_service_Environment' if service_env.get('XAUTHORITY') else
             'actual_X_server_-auth_argument' if server['auth_argument'] else
             'actual_X_server_XAUTHORITY_environment' if selected_auth else
             'none_explicit_in_GUI_service_or_actual_X_server_same_root_user_default')
auth_path=Path(selected_auth) if selected_auth else None
if auth_path is not None:
    assert auth_path.is_absolute() and auth_path.is_file()
    # Metadata only. Never open/read/copy the Xauthority credential.
    assert auth_path.stat().st_uid==0
env=dict(os.environ,DISPLAY=display,HOME=pwd.getpwuid(0).pw_dir)
env.pop('XAUTHORITY',None)
if auth_path is not None:env['XAUTHORITY']=str(auth_path)
query=subprocess.run(['xset','q'],env=env,capture_output=True,text=True,timeout=8)
result={'schema':'aura-x11-power-readonly-1','boot_id':BOOT,
    'board_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'startup_sha256':STARTUP_SHA,'display':display,'display_source':'current_pinned_GUI_startup_config',
    'xauthority_path':str(auth_path) if auth_path is not None else None,'xauthority_source':auth_source,
    'x_server_access_control_disabled_argument':server['access_control_disabled_argument'],
    'x_server_pid':server['pid'],'x_server_birth_ticks':server['birth_ticks'],
    'x_server_command_sha256':server['command_sha256'],
    'xset_query_succeeded':query.returncode==0,'xset_exit_code':query.returncode,
    'screensaver_timeout_seconds':None,'screensaver_cycle_seconds':None,
    'dpms_enabled':None,'monitor_power':None,
    'command_executed':'xset q','xauthority_contents_read':False,'full_environment_exported':False,
    'screen_or_private_data_exported':False,'power_policy_changed':False,'wake_command_sent':False,
    'services_started_or_stopped':False,'board_mutations':False}
if query.returncode==0:
    screen=re.search(r'\btimeout:\s*(\d+)\s+cycle:\s*(\d+)',query.stdout)
    enabled=re.search(r'\bDPMS is (Enabled|Disabled)\b',query.stdout)
    monitor=re.search(r'\bMonitor is (On|Off|Standby|Suspend)\b',query.stdout)
    assert screen is not None and enabled is not None and monitor is not None,'Unrecognized xset metadata'
    result.update(screensaver_timeout_seconds=int(screen[1]),screensaver_cycle_seconds=int(screen[2]),
                  dpms_enabled=enabled[1]=='Enabled',monitor_power=monitor[1])
assert hashlib.sha256(STARTUP.read_bytes()).hexdigest()==STARTUP_SHA
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert (Path('/proc')/str(server['pid'])/'stat').read_text().rsplit(')',1)[1].split()[19]==server['birth_ticks']
print(json.dumps(result,sort_keys=True))
