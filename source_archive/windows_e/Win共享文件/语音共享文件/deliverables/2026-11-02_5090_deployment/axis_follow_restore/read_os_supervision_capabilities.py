"""Inspect existing OS supervision capabilities; does not create a unit or run a client."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
transport=HERE.parents[1]/'2026-10-18_board_dialogue/board_ssh.py'
spec=importlib.util.spec_from_file_location('axis_os_capability_reader',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
source="""import datetime,hashlib,json,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='903cfade-b93c-48fa-804e-379be1967313'
results=[]
for argv in (['systemd-run','--version'],['systemd-run','--help'],
    ['systemctl','show','aura-camera-ui.service','--property=Restart,KillMode,SendSIGKILL,TimeoutStopUSec,ExecStart,ExecCondition'],
    ['systemctl','show','--property=DefaultTimeoutStartUSec,DefaultTimeoutStopUSec']):
    r=subprocess.run(argv,capture_output=True,text=True,timeout=10)
    results.append({'argv':argv,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
client=Path('/usr/bin/dfx-mgr-client');binary=Path('/usr/lib/systemd/systemd')
if not binary.is_file():binary=Path('/lib/systemd/systemd')
data=binary.read_bytes()
print(json.dumps({'board_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':'903cfade-b93c-48fa-804e-379be1967313',
 'commands':results,'client_sha256':hashlib.sha256(client.read_bytes()).hexdigest(),
 'systemd_binary_path':str(binary),'systemd_binary_sha256':hashlib.sha256(data).hexdigest(),
 'systemd_binary_contains_append_prefix':b'append:' in data,
 'systemd_binary_contains_runtime_max':b'RuntimeMaxSec' in data,
 'systemd_binary_contains_standard_output':b'StandardOutput' in data,
 'transient_service_created':False,'client_executed':False,'board_mutations':False}))
"""
value=json.loads(module.ssh('python3 -B -',source,timeout=45))
target=HERE/'os_supervision_capabilities_01.json'
with target.open('x',encoding='utf-8') as stream:
    json.dump({'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'board_result':value},stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps({'output':str(target),'board_result':value}))
