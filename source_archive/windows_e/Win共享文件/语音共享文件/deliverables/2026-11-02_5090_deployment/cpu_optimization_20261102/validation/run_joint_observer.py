"""Host launcher. Must receive a fresh expected-owner receipt; never toggles UI."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--expected',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--duration',type=float,default=180)
    parser.add_argument('--interval',type=float,default=.5)
    args=parser.parse_args()
    expected=json.loads(args.expected.read_text(encoding='utf-8'))
    assert isinstance(expected,dict) and set(expected['owners'])>={'gui','camera'}
    assert 1<=args.duration<=300 and .25<=args.interval<=2
    assert not args.output_dir.exists()
    args.output_dir.mkdir(parents=True)
    source=Path(__file__).with_name('observe_joint_readonly.py').read_text(encoding='utf-8')
    code='EXPECTED = '+repr(expected)+'\n'+source
    compile(code,'<read-only-joint-observer>','exec')
    key=Path.home()/'.ssh/aura_5090_board_ed25519'
    known=Path.home()/'.ssh/aura_migration_known_hosts'
    assert key.is_file() and known.is_file()
    executable=shutil.which('ssh.exe') or shutil.which('ssh')
    assert executable
    argv=[executable,'-i',str(key),'-o','UserKnownHostsFile='+str(known),
        '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
        '-o','ConnectTimeout=4','root@192.168.50.2',
        '/usr/bin/python3 -B -I -S - --duration '+str(args.duration)+' --interval '+str(args.interval)]
    process=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
    receipt={'host_started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'ssh_pid':process.pid,'source_sha256_lf':hashlib.sha256(code.encode()).hexdigest(),
        'expected_receipt_sha256':hashlib.sha256(args.expected.read_bytes()).hexdigest(),
        'controls_available':False}
    (args.output_dir/'observer_owner.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    process.stdin.write(code);process.stdin.close()
    with (args.output_dir/'observations.jsonl').open('x',encoding='utf-8') as stream:
        for line in process.stdout:
            value=json.loads(line);value['host_observed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
            stream.write(json.dumps(value,separators=(',',':'))+'\n');stream.flush()
            if value.get('event') in ('BASELINE','TURN_COMPLETED','FINISHED'):
                print(json.dumps({key:value[key] for key in ('event','utc','ordinal','completed_new_turns','actual_duration_seconds') if key in value}),flush=True)
    error=process.stderr.read();rc=process.wait()
    (args.output_dir/'observer_exit.json').write_text(json.dumps({'exit_code':rc,
        'stderr_present':bool(error),'host_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n',encoding='utf-8')
    if rc:raise SystemExit('Read-only observer exited with code '+str(rc)+'; inspect current owners/startup before a new run.')

if __name__=='__main__':main()
