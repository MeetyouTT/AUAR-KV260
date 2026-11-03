from pathlib import Path
import json,subprocess
root=Path('/home/root/aura-yuki-validation-20261030/native_integration')
assert json.loads((root/'host-build-result.json').read_text())['status']=='PASS'
pidfile=root/'host-test-pid.json'
if pidfile.exists():
    old=json.loads(pidfile.read_text());path=Path('/proc',str(old.get('pid',0)),'cmdline')
    if path.exists() and b'host_test_worker.py' in path.read_bytes():raise RuntimeError('Previous host tests still active')
with (root/'host-test-launch.log').open('w') as log:
    child=subprocess.Popen(['python3',str(root/'host_test_worker.py')],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
pidfile.write_text(json.dumps({'pid':child.pid}));print(json.dumps({'test_pid':child.pid}))
