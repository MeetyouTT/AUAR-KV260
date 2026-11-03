"""Read simulated acceptance trace and live progress; no driver/camera writes."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

root = Path('/home/root/aura-realtime-vision-20261007')
current = json.loads((root/'current.json').read_text())
run, release = Path(current['run_root']), Path(current['release'])
before = json.loads((run/'status.json').read_text())
time.sleep(3)
after = json.loads((run/'status.json').read_text())
trace_file = run/'motion-simulation.jsonl'
trace = trace_file.read_bytes()
events = [json.loads(line) for line in trace.decode().splitlines()]
accepted = [e for e in events if e['motion_simulation']['control'].get('receipt',{}).get('outcome')=='ACCEPTED']
apps = subprocess.run(['xmutil','listapps'],capture_output=True,text=True,timeout=10)
rows = [r for r in apps.stdout.splitlines() if r.split() and r.split()[0]=='kv260-benchmark-b4096']
hashes_ok = all(hashlib.sha256((release/name).read_bytes()).hexdigest()==digest
                for name,digest in current['files'].items())
passed = (hashes_ok and apps.returncode==0 and len(rows)==1 and rows[0].split()[-1].rstrip(',')=='0'
          and all(after[k]>before[k] for k in ['capture_frames','detected_frames','rendered_frames'])
          and not after['error'] and not after['stopped'] and events
          and all(not e['motion_simulation']['motion_command_emitted']
                  and not e['motion_simulation']['physical_actuation_authorized'] for e in events)
          and after['motion_simulation']['scope']=='SIMULATED')
print(json.dumps({'passed':bool(passed),'pid':current['pid'],'run_root':str(run),
                  'before':before,'after':after,'hashes_valid':hashes_ok,
                  'trace_sha256':hashlib.sha256(trace).hexdigest(),'trace_event_count':len(events),
                  'accepted_entries':accepted[-8:],'events_tail':events[-12:],
                  'apps':apps.stdout,'motion_command_emitted':False,'fpga_modified':False}))
assert passed
