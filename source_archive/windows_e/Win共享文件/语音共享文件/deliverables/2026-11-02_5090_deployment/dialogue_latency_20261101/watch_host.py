"""Stream filtered board observations to host JSONL with strict SSH host verification."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

parser=argparse.ArgumentParser()
parser.add_argument('--run-label',required=True,choices=('observation02',))
args=parser.parse_args()
SOURCE_ROOT=Path(__file__).resolve().parent
HERE=SOURCE_ROOT/args.run_label
HERE.mkdir(exist_ok=False)
source=SOURCE_ROOT/'watch_board_latency.py';raw=source.read_bytes()
output=HERE/'observations.jsonl';assert not output.exists()
key=Path.home()/'.ssh/aura_5090_board_ed25519';known=Path.home()/'.ssh/aura_migration_known_hosts'
assert key.is_file() and known.is_file()
argv=[shutil.which('ssh.exe') or shutil.which('ssh'),'-i',str(key),'-o','UserKnownHostsFile='+str(known),
    '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=4',
    'root@192.168.50.2','python3 -B - --observe-only']
process=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
owner={'host_started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ssh_pid':process.pid,
    'script_sha256':hashlib.sha256(raw).hexdigest(),'output':str(output)}
(HERE/'observer_owner.json').write_text(json.dumps(owner,indent=2)+'\n',encoding='utf-8')
process.stdin.write(raw.decode('utf-8'));process.stdin.close()
with output.open('x',encoding='utf-8') as stream:
    for line in process.stdout:
        value=json.loads(line)
        value['host_observed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        stream.write(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n');stream.flush()
        if value.get('event')!='SAMPLE':
            print(json.dumps({k:v for k,v in value.items() if k in ('event','utc','ordinal','completed_new_turns','hf_state','hf_enabled','microphone_open','board_mono','ready_seen')}) ,flush=True)
error=process.stderr.read();rc=process.wait()
(HERE/'observer_exit.json').write_text(json.dumps({'exit_code':rc,'stderr_present':bool(error),
    'host_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n',encoding='utf-8')
if rc:
    print(error.encode('ascii','backslashreplace').decode(),file=sys.stderr)
    raise SystemExit(rc)
