import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
helper=HERE.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('gui_reconcile_transport',helper)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
code=r'''
import datetime,hashlib,json,subprocess
from pathlib import Path
units={}
for name in ('aura-avatar-ui.service','aura-camera-ui.service'):
    p=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Job,Result,ExecMainCode,ExecMainStatus,ExecMainStartTimestamp,ExecMainExitTimestamp,NRestarts'],capture_output=True,text=True,timeout=4)
    assert p.returncode==0
    units[name]=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
startup=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
owners=[]
for name,unit in units.items():
    pid=int(unit['MainPID'])
    if not pid:continue
    root=Path('/proc')/str(pid)
    try:owners.append({'unit':name,'pid':pid,'birth':(root/'stat').read_text().rsplit(')',1)[1].split()[19],'cmd_sha256':hashlib.sha256((root/'cmdline').read_bytes()).hexdigest()})
    except OSError:pass
native=[]
for root in Path('/proc').iterdir():
    if not root.name.isdigit():continue
    try:maps=(root/'maps').read_text()
    except OSError:continue
    if 'libvsrv.so' in maps or '/dev/mem' in maps:native.append(int(root.name))
journal=subprocess.run(['journalctl','-u','aura-avatar-ui.service','-n','80','--no-pager','-o','json'],capture_output=True,text=True,timeout=5)
messages=[]
allowed=('clock','Clock','Traceback','Error','Exception','failed','Failed','exited','status=','Stopped','Started','Stopping','worker','BUSY')
for line in journal.stdout.splitlines():
    try:entry=json.loads(line);message=entry.get('MESSAGE','')
    except (ValueError,TypeError):continue
    # Only fixed error/diagnostic signatures are exported, never raw log lines.
    hits=[word for word in allowed if word in message]
    if hits:messages.append({'timestamp_us':entry.get('__REALTIME_TIMESTAMP'),'signatures':hits,
        'mentions_ClockUnavailable':'ClockUnavailable' in message,
        'mentions_database_busy':'database' in message.lower() and 'busy' in message.lower(),
        'mentions_sigterm':'SIGTERM' in message or 'status=15/TERM' in message,
        'mentions_clean_exit':'status=0/SUCCESS' in message})
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'units':units,'owners':owners,
    'startup_sha256':hashlib.sha256(startup.read_bytes()).hexdigest(),
    'motion_map_owners':native,'filtered_journal_signatures':messages,
    'cpu_transaction_directory_exists':Path('/home/root/aura-5090-recovery-20261102-903cfade/cpu-optimization-20261102-v1').exists(),
    'read_only':True,'stop_sent':False}))
'''
value=json.loads(module.ssh('/usr/bin/python3 -B -I -S -',code,timeout=20))
output=HERE/'GUI_OWNER_RECONCILE.json'
with output.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(value))
