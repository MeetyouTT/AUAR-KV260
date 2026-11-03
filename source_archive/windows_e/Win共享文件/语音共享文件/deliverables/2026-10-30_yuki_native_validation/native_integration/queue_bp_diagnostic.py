from pathlib import Path
import subprocess,json
root=Path('/home/root/aura-yuki-validation-20261030/native_integration')
worker=root/'bp_diagnostic_worker.py'
worker.write_text('''from pathlib import Path
import json,subprocess,time
root=Path('/home/root/aura-yuki-validation-20261030/native_integration');deadline=time.monotonic()+600
while True:
 state=json.loads((root/'results/optimized-test-result.json').read_text())['status']
 if state not in ('WAITING_BUILD','RUNNING'):break
 if time.monotonic()>deadline:raise RuntimeError('Timed test did not finish; do not overlap GPU tests')
 time.sleep(3)
with (root/'results/bp-diagnostic.log').open('w') as log:
 child=subprocess.run(['python3',str(root/'render_bp_diagnostic.py')],stdout=log,stderr=subprocess.STDOUT,timeout=60)
(root/'results/bp-diagnostic-result.json').write_text(json.dumps({'returncode':child.returncode}))
''')
with (root/'bp-diagnostic-launch.log').open('w') as log:
    child=subprocess.Popen(['python3',str(worker)],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
print(json.dumps({'queued_pid':child.pid,'waits_for':'optimized GTK timed test to finish'}))
